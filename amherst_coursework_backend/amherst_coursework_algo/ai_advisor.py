"""
AI Course Advisor using Google Gemini
Provides personalized course recommendations and schedule analysis
"""

from google import genai
from google.genai import types
from django.conf import settings
import json
import threading
import re
from functools import lru_cache

# Module-level client instance for reuse
_client = None
_client_lock = threading.Lock()

# System instruction for the AI advisor
ADVISOR_SYSTEM_INSTRUCTION = """You are an expert academic advisor for Amherst College with access to the course catalog search system. Your role is to:

1. **Analyze student schedules** for balance, workload, and academic diversity
2. **Search the course catalog** to find relevant courses based on student interests
3. **Recommend courses** that align with student interests and complement their current schedule
4. **Explain prerequisites** and course sequences clearly
5. **Consider practical factors** like time conflicts, credit load, and department distribution
6. **Be encouraging and supportive** while providing honest, helpful advice with Amherst's unique open-curriculum in mind.

When analyzing a schedule:
- Check total credit load (typical is 16 credits per semester, 12-20 is normal range)
- Look for department diversity (taking courses from multiple areas is beneficial)
- Consider workload balance (mixing intensive and lighter courses)
- Identify potential prerequisite chains for future planning

When the student asks for course suggestions:
- Think about what topics, departments, or skills would complement their schedule
- You have access to search the course catalog by keywords, departments, topics, professors, etc.
- Search for courses that match the student's interests and needs
- The search system understands natural language queries like "statistics", "creative writing", "environmental science", "social justice", etc.

When recommending courses:
- Suggest 3-6 specific courses with clear reasoning
- **DO NOT recommend courses the student is already taking** (check their current schedule)
- **ALWAYS use the exact course code format** (e.g., COSC-111, STAT-135, ENGL-225, SOCI-230)
- **Mention each course code only ONCE** in your entire response
- Explain how each course connects to their current interests
- Mention any prerequisites or special considerations
- Group recommendations by category when helpful (e.g., "Quantitative Reasoning", "Humanities")

Format each recommendation clearly:
**COURSE-CODE: Course Title**
- Why it fits: [explanation]
- Prerequisites: [if any]

Be conversational, friendly, and concise. Use bullet points and headers for clarity.

DO NOT output tables or repeat course codes.
"""

# Model configuration
MODEL_CONFIG = {
    "temperature": 0.7,
    "top_p": 0.9,
    "max_output_tokens": 20480,
}


def _get_genai_client():
    """Get or create a shared GenAI client instance"""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:  # Double-check after acquiring lock
                if not settings.GEMINI_API_KEY:
                    raise Exception("GEMINI_API_KEY not configured in settings")
                _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def search_courses(query, all_courses):
    """
    Search for courses using the masked_filters search functionality
    
    Args:
        query: Search query string
        all_courses: QuerySet of all available courses
    
    Returns:
        list: Filtered and ranked courses matching the query
    """
    from .masked_filters import filter as search_filter
    
    try:
        # Convert QuerySet to list for the filter function
        courses_list = list(all_courses)
        
        # Use the existing search/filter functionality
        filtered_courses = search_filter(query, courses_list)
        
        # Return top 20 results
        return filtered_courses[:20]
    except Exception as e:
        print(f"Error searching courses: {e}")
        return []


def build_course_context(cart_courses, all_courses_sample=None):
    """
    Build rich context about student's schedule and available courses
    
    Args:
        cart_courses: List of Course model instances in student's cart
        all_courses_sample: Optional sample of available courses for recommendations
    
    Returns:
        dict: Structured context for the AI
    """
    # Analyze current schedule
    current_schedule = []
    total_credits = 0
    departments = set()
    keywords = set()
    
    for course in cart_courses:
        course_info = {
            'name': course.courseName,
            'codes': [code.value for code in course.courseCodes.all()],
            'description': course.courseDescription[:300] if course.courseDescription else '',
            'credits': course.credits,
            'departments': [d.name for d in course.departments.all()],
            'keywords': [k.name for k in course.keywords.all()[:5]],
            'professor': [p.name for p in course.professors.all()],
        }
        current_schedule.append(course_info)
        total_credits += course.credits
        departments.update(course_info['departments'])
        keywords.update(course_info['keywords'])
    
    # Build context dictionary
    context = {
        'current_schedule': current_schedule,
        'total_credits': total_credits,
        'num_courses': len(cart_courses),
        'departments_covered': list(departments),
        'common_keywords': list(keywords)[:10],
    }
    
    # Add sample of available courses if provided
    if all_courses_sample:
        context['available_courses_sample'] = [
            {
                'name': c.courseName,
                'codes': [code.value for code in c.courseCodes.all()],
                'description': c.courseDescription[:200] if c.courseDescription else '',
                'credits': c.credits,
                'departments': [d.name for d in c.departments.all()],
            }
            for c in all_courses_sample[:50]  # Limit to 50 courses
        ]
    
    return context


def generate_advisor_response(context, user_question=None):
    """
    Generate AI advisor response using Gemini
    
    Args:
        context: dict with schedule and course information
        user_question: Optional specific question from user
    
    Returns:
        str: AI-generated advice and recommendations
    """
    try:
        client = _get_genai_client()
        
        # Build the prompt
        if not user_question or user_question.strip() == '':
            user_question = "Please analyze my current schedule and suggest courses I should consider adding."
        
        # Build the prompt with available courses if provided
        available_courses_text = ""
        if 'available_courses_sample' in context and context['available_courses_sample']:
            available_courses_text = "\n\nRelevant Available Courses (searched based on student's interests):\n"
            for course in context['available_courses_sample'][:30]:  # Limit to 30 for token efficiency
                codes = ', '.join(course['codes'])
                depts = ', '.join(course['departments'])
                available_courses_text += f"- {codes}: {course['name']} ({depts}, {course['credits']} credits)\n"
                if course['description']:
                    available_courses_text += f"  {course['description'][:150]}...\n"
        
        prompt_parts = [
            types.Part.from_text(text=f"""
Student's Current Schedule:
{json.dumps(context['current_schedule'], indent=2)}

Summary:
- Total Credits: {context['total_credits']}
- Number of Courses: {context['num_courses']}
- Departments: {', '.join(context['departments_covered']) if context['departments_covered'] else 'None yet'}
- Key Topics: {', '.join(context['common_keywords'][:5]) if context['common_keywords'] else 'None yet'}
{available_courses_text}

Student Question: {user_question}

Please provide helpful advice and specific course recommendations from the available courses listed above.

Please provide helpful advice and specific course recommendations.
""")
        ]
        
        # Create chat and send message
        chat = client.chats.create(
            model='models/gemini-flash-latest',
            config={
                "system_instruction": ADVISOR_SYSTEM_INSTRUCTION,
                **MODEL_CONFIG
            }
        )
        
        response = chat.send_message(prompt_parts)
        
        if response and response.text:
            return response.text
        else:
            return "I apologize, but I couldn't generate a response. Please try again."
            
    except Exception as e:
        print(f"Error generating advisor response: {e}")
        raise Exception(f"Failed to generate advice: {str(e)}")


def parse_recommendations_from_response(response_text, available_courses):
    """
    Extract course recommendations from AI response and match to actual courses
    
    Args:
        response_text: str - AI generated response
        available_courses: QuerySet - Available courses to match against
    
    Returns:
        list: Matched course objects with recommendation reasons
    """
    import re
    from .models import CourseCode
    
    recommendations = []
    seen_course_ids = set()  # Track courses we've already added
    
    # Look for course codes like "COSC-111", "MATH-271", "SOCI-230", etc.
    course_code_pattern = r'\b([A-Z]{4}-\d{3}[A-Z]?)\b'
    
    # Find all course codes with their positions in the text
    matches = [(m.group(1), m.start()) for m in re.finditer(course_code_pattern, response_text)]
    
    # Process each unique course code
    for code, position in matches:
        try:
            # Find course by code
            course_code_obj = CourseCode.objects.filter(value=code).first()
            if not course_code_obj:
                continue
                
            course = course_code_obj.courses.first()
            if not course or course.id in seen_course_ids:
                continue
            
            # Mark this course as seen
            seen_course_ids.add(course.id)
            
            # Extract context around the course code for better reason
            # Look for the paragraph or section containing this code
            reason = extract_course_reason(response_text, code, position)
            
            recommendations.append({
                'course': course,
                'reason': reason
            })
            
            # Limit to 6 recommendations to avoid overwhelming the user
            if len(recommendations) >= 6:
                break
                
        except Exception as e:
            print(f"Error matching course code {code}: {e}")
            continue
    
    return recommendations


def extract_course_reason(text, course_code, position):
    """
    Extract the reason/context for a course recommendation
    
    Args:
        text: Full response text
        course_code: The course code to find context for
        position: Position of the course code in the text
    
    Returns:
        str: Extracted reason text
    """
    # Split text into lines
    lines = text.split('\n')
    
    # Find which line contains the course code
    current_pos = 0
    target_line_idx = 0
    
    for idx, line in enumerate(lines):
        if current_pos <= position < current_pos + len(line):
            target_line_idx = idx
            break
        current_pos += len(line) + 1  # +1 for newline
    
    # Look for the section containing this course
    # Start from the line with the course code and look backwards for a header
    section_start = target_line_idx
    for i in range(target_line_idx, max(0, target_line_idx - 10), -1):
        line = lines[i].strip()
        # Check if this line looks like a header (starts with #, **, or is short and ends with :)
        if (line.startswith('#') or 
            line.startswith('**') or 
            (len(line) < 80 and line.endswith(':'))):
            section_start = i
            break
    
    # Extract the section (header + next few lines)
    section_lines = []
    for i in range(section_start, min(len(lines), target_line_idx + 5)):
        line = lines[i].strip()
        if line:
            section_lines.append(line)
        # Stop if we hit another course code (different from ours)
        if i > target_line_idx and re.search(r'\b[A-Z]{4}-\d{3}[A-Z]?\b', line):
            other_code = re.search(r'\b([A-Z]{4}-\d{3}[A-Z]?)\b', line).group(1)
            if other_code != course_code:
                break
    
    # Join the section and clean it up
    reason = ' '.join(section_lines)
    
    # Remove markdown formatting for cleaner display
    reason = re.sub(r'\*\*([^*]+)\*\*', r'\1', reason)  # Remove **bold**
    reason = re.sub(r'\*([^*]+)\*', r'\1', reason)      # Remove *italic*
    reason = re.sub(r'^#+\s+', '', reason)              # Remove ### headers
    
    # Limit length
    if len(reason) > 250:
        reason = reason[:247] + '...'
    
    # If we couldn't extract a good reason, provide a default
    if not reason or len(reason) < 20:
        reason = f"Recommended to complement your current schedule"
    
    return reason


def get_cache_stats():
    """Get statistics about the advisor service"""
    return {
        'client_initialized': _client is not None,
        'model': 'gemini-flash-latest',
    }
