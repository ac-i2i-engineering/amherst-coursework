const CODE_TO_NAME = JSON.parse(document.getElementById('dept-dict').textContent);

let globalCourseList = [];

// Add debounce function at the top of your file
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function handleSearch() {
    const searchQuery = document.getElementById('searchInput').value.toLowerCase().trim();
    
    // For empty queries, show all courses
    if (!searchQuery) {
        document.querySelectorAll('.course-card').forEach(card => {
            card.classList.remove('hidden');
        });
        return;
    }
    
    // For very short queries (1-2 chars), consider showing a message
    if (searchQuery.length < 2) {
        alert('Please enter a more specific search term');
        return;
    }
    
    // Continue with backend search
    search_filter(searchQuery, 0.1);
}

/* Add this to your script section */
function handleCartClick(event, courseId) {
    event.stopPropagation();  // Prevent event from bubbling up to course-card
    toggleCart(courseId);
}

function toggleCartPanel() {
    const panel = document.getElementById('cart-side-panel');
    panel.classList.toggle('open');
    updateCartDisplay();
}

// Find courses with same meeting time and apply styling
function findAndMarkAllCartConflicts() {    
    // Get all courses in cart
    const cartIds = JSON.parse(localStorage.getItem('courseCart') || '[]');
    
    // Always clear all existing conflict styling first
    document.querySelectorAll('.course-card').forEach(card => {
        card.classList.remove('time-conflict');
        card.style.border = '';
        card.style.backgroundColor = '';
        
        const existingBadge = card.querySelector('.conflict-badge');
        if (existingBadge) existingBadge.remove();
    });
    
    // If cart is empty, we're done (all styling cleared)
    if (cartIds.length === 0) {
        localStorage.removeItem('courseTimeConflicts'); // Clear stored conflicts
        return;
    }
    
    // Initialize courseConflicts object to store all conflicts
    const courseConflicts = {};
    
    // Process each cart course
    cartIds.forEach(cartCourseId => {
        // Find the course card
        const cartCard = document.querySelector(`.course-card[data-course-id="${cartCourseId}"]`);
        if (!cartCard) {
            return; // Skip this iteration
        }
        
        // Get the course name for better messages
        const cartCourseName = cartCard.querySelector('.course-name')?.textContent || 'Unknown Course';
        
        // Get the meeting time info
        const cartInfoText = cartCard.querySelector('.info-text')?.textContent;
        if (!cartInfoText) {
            return;
        }
        
        // Extract meeting times
        const cartMeetingTime = cartInfoText.split('|')[1]?.trim();
        if (!cartMeetingTime) {
            return;
        }
        
        // Track conflicts for this cart course
        const conflictsForThisCourse = [];
        
        // Find all non-cart courses with matching meeting times
        document.querySelectorAll('.course-card').forEach(card => {
            const courseId = card.dataset.courseId;
            // Skip if this course is in cart
            if (cartIds.includes(courseId)) return;
            
            const infoText = card.querySelector('.info-text')?.textContent;
            if (!infoText) return;
            
            const meetingTime = infoText.split('|')[1]?.trim();
            
            // Simple direct string comparison of meeting times
            if (meetingTime && meetingTime === cartMeetingTime) {
                const courseName = card.querySelector('.course-name')?.textContent || 'Unknown';
                
                // Add to our tracking array
                conflictsForThisCourse.push({
                    id: courseId,
                    name: courseName
                });
                
                // Apply styling
                card.classList.add('time-conflict');
                card.style.border = '2px solid #ff817a';
                card.style.backgroundColor = 'rgba(255,0,0,0.07)';
                
                // Add a badge
                const badge = document.createElement('div');
                badge.className = 'conflict-badge';
                badge.textContent = '⚠️ CONFLICT';
                badge.style.position = 'absolute';
                badge.style.top = '18px';
                badge.style.right = '50px';
                badge.style.backgroundColor = '#ff0000';
                badge.style.color = 'white';
                badge.style.padding = '3px 6px';
                badge.style.borderRadius = '3px';
                badge.style.fontSize = '12px';
                badge.style.fontWeight = 'bold';
                badge.style.zIndex = '100';
                badge.title = `Conflicts with ${cartCourseName}`;
                
                // Set position relative if needed
                if (getComputedStyle(card).position === 'static') {
                    card.style.position = 'relative';
                }
                
                card.appendChild(badge);
            }
        });
        
        // Store conflicts for this cart course
        courseConflicts[cartCourseId] = conflictsForThisCourse.map(c => c.id);
    });
    
    // Store all conflicts
    localStorage.setItem('courseTimeConflicts', JSON.stringify(courseConflicts));
}

// Update your toggleCart function to use findAndMarkAllCartConflicts
function toggleCart(courseId) {
    // Get existing cart or initialize empty array
    let cart = JSON.parse(localStorage.getItem('courseCart') || '[]');
    
    // Check if course is already in cart
    let courseIndex = cart.indexOf(courseId);
    
    if (event) {
        event.stopPropagation();
    }
    
    if (courseIndex === -1) {
        cart.push(courseId);
        updateButtonState(courseId, true);
    } else {
        cart.splice(courseIndex, 1);
        updateButtonState(courseId, false);
    }

    // Save updated cart
    localStorage.setItem('courseCart', JSON.stringify(cart));
    updateCartDisplay();
    
    // Update this line to check all cart courses
    setTimeout(findAndMarkAllCartConflicts, 500);
}

// Update your conflict highlighting function to use the stored conflicts
function highlightTimeConflicts() {
    findAndMarkAllCartConflicts();

    // Get courses in cart
    const cartIds = JSON.parse(localStorage.getItem('courseCart') || '[]');
    
    // Reset all course cards first
    document.querySelectorAll('.course-card').forEach(card => {
        card.classList.remove('time-conflict');
        card.style.border = '';
        
        const existingBadge = card.querySelector('.conflict-badge');
        if (existingBadge) existingBadge.remove();
    });
    
    if (cartIds.length === 0) return;
    
    // Get stored conflicts
    const courseConflicts = JSON.parse(localStorage.getItem('courseTimeConflicts') || '{}');
    
    // Check each course card for conflicts with cart courses
    document.querySelectorAll('.course-card').forEach(card => {
        const courseId = card.dataset.courseId;
        
        // Skip courses already in cart
        if (cartIds.includes(courseId)) return;
        
        // Check if any cart course conflicts with this course
        let hasConflict = false;
        
        cartIds.forEach(cartCourseId => {
            // Check if this cart course has conflicts with the current card
            if (courseConflicts[cartCourseId] && 
                courseConflicts[cartCourseId].includes(courseId)) {
                hasConflict = true;
            }
        });
        
        if (hasConflict) {
            card.classList.add('time-conflict');
        }
    });
}

function toggleCart(courseId) {
    // Get existing cart or initialize empty array
    let cart = JSON.parse(localStorage.getItem('courseCart') || '[]');
    
    // Check if course is already in cart
    let courseIndex = cart.indexOf(courseId)
    
    if (event) {
        event.stopPropagation();
    }
    
    if (courseIndex === -1) {
        cart.push(courseId);
        updateButtonState(courseId, true);
    } else {
        cart.splice(courseIndex, 1);
        updateButtonState(courseId, false);
    }

    // Save updated cart
    localStorage.setItem('courseCart', JSON.stringify(cart));
    updateCartDisplay();
    
    // Add this line to highlight conflicts when cart changes
    setTimeout(findAndMarkAllCartConflicts, 500);
}

function updateButtonState(courseId, inCart) {
    document.querySelectorAll(`.cart-button[data-course-id="${courseId}"]`).forEach(button => {
        const icon = button.querySelector('i');
        if (inCart) {
            icon.className = 'fa-solid fa-check';
            button.classList.add('in-cart');
        } else {
            icon.className = 'fa-solid fa-plus';
            button.classList.remove('in-cart');
        }
    });
}

function togglePanel(courseId = null) {
    const panel = document.getElementById('side-panel');
    const panelContent = document.getElementById('panel-content');
    const mainContent = document.querySelector('.main-content');
    const courseContainer = document.querySelector('.course-container');

    if (courseId) {
        const clickedCard = document.querySelector(`.course-card[data-course-id="${courseId}"]`);
        
        // Show loading state
        panelContent.innerHTML = '<div class="loading">Loading...</div>';
        panel.classList.add('open');

        fetch(`/details/${courseId}/`)  
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Failed to load course details: ${response.status}`);
                }
                return response.text();
            })
            .then(html => {
                // Reset scroll position before loading new content
                panel.scrollTop = 0;
                panelContent.scrollTop = 0;
                
                // Update content and show panel
                panelContent.innerHTML = html;
                mainContent.classList.add('shifted');
                courseContainer.classList.add('shifted');

                // Scroll to clicked card
                if (clickedCard) {
                    clickedCard.scrollIntoView({ 
                        behavior: 'smooth', 
                        block: 'center'
                    });
                }
            })
            .catch(error => {
                console.error('Error:', error);
                panelContent.innerHTML = '<div class="error">Failed to load course details</div>';
            });
    } else {
        // Closing panel
        courseContainer.style.opacity = '0';
        courseContainer.classList.add('hidden');
        panel.classList.add('closing');

        document.querySelectorAll('.course-card').forEach(card => {
            card.classList.remove('active');
        });
        
        setTimeout(() => {
            panel.classList.remove('open');
            panel.classList.remove('closing');
            mainContent.classList.remove('shifted');
            courseContainer.classList.remove('shifted');
            
            // Fade content back in only after panel is closed and layout is adjusted
            setTimeout(() => {
                courseContainer.classList.add('fade-in');
                courseContainer.classList.remove('hidden');
                courseContainer.style.opacity = '1';
                
                setTimeout(() => {
                    courseContainer.classList.remove('fade-in');
                }, 300);
            }, 200);
        }, 600);
    }
}


// Add this function to initialize courses
async function initializeCourses() {
    const courseCards = document.querySelectorAll('.course-card');
    
    // Fetch all courses once
    await Promise.all(Array.from(courseCards).map(async (card, index) => {
        const courseId = card.dataset.courseId;
        const course = await getCourseById(courseId);
        if (course) {
            globalCourseList[index] = course;
        }
    }));
}

async function getCourseById(courseId) {
    try {
        const response = await fetch(`/api/course/${courseId}/`);
        if (!response.ok) {
            throw new Error('Course not found');
        }
        const data = await response.json();
        return data.course;
    } catch (error) {
        console.error('Error fetching course:', error);
        return null;
    }
}

async function search_filter(searchQuery, similarityThreshold) {
    searchQuery = searchQuery.toLowerCase().trim();
    const courseCards = document.querySelectorAll('.course-card');
    const courseContainer = document.querySelector('.course-container'); 
    
    // Add loading indicator
    document.getElementById('search-loading').style.display = 'inline-block';
    
    // Get course IDs from data attributes
    const courseIds = Array.from(courseCards).map(card => card.dataset.courseId);
    
    // Get indicators from backend
    const indicators = await filterCoursesByMask(searchQuery, courseIds, similarityThreshold);

    courseCount = 0
    // Update visibility based on indicators
    courseCards.forEach((card, index) => {
        if (indicators[index]) {
            card.classList.remove('hidden');
            courseCount += 1;
        } else {
            card.classList.add('hidden');
        }
    });

    if (courseCount === 0) {
        // Remove existing no-results message if it exists
        const existingMessage = courseContainer.querySelector('.no-results-message');
        if (existingMessage) {
            existingMessage.remove();
        }
        
        // Create and add new no-results message
        const noResultsMessage = document.createElement('div');
        noResultsMessage.className = 'no-results-message';
        noResultsMessage.innerHTML = `No results available for "${searchQuery}"`;
        courseContainer.appendChild(noResultsMessage);
    } else {
        // Remove no-results message if it exists
        const noResultsMessage = courseContainer.querySelector('.no-results-message');
        if (noResultsMessage) {
            noResultsMessage.remove();
        }
    }
    
    // Hide loading indicator
    document.getElementById('search-loading').style.display = 'none';
}

async function filterCoursesByMask(searchQuery, courseIds, similarityThreshold) {
    try {
        // Get CSRF token from cookie if not available in the form
        let csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        
        // If no CSRF token in form, try to get from cookie
        if (!csrftoken) {
            csrftoken = getCookie('csrftoken');
        }
        
        const headers = {
            'Content-Type': 'application/json',
        };
        
        // Only add CSRF token if we found one
        if (csrftoken) {
            headers['X-CSRFToken'] = csrftoken;
        }
        
        const response = await fetch('/api/masked_filter/', {
            method: 'POST',
            headers: headers,
            credentials: 'include',  // Add this line to include cookies
            body: JSON.stringify({
                search_query: searchQuery,
                course_ids: courseIds,
                similarity_threshold: similarityThreshold
            })
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            return data.indicators;
        }
        console.error('Error:', data.message);
        return new Array(courseIds.length).fill(0);
        
    } catch (error) {
        console.error('Error:', error);
        return new Array(courseIds.length).fill(0);
    }
}

// Helper function to get cookie by name (for CSRF token)
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function updateCartDisplay() {
    const cartIds = JSON.parse(localStorage.getItem('courseCart') || '[]');
    const cartCount = document.getElementById('cart-count');
    const cartCountHeader = document.getElementById('cart-count-header');
    const cartCoursesList = document.getElementById('cart-courses-list');
    
    // Update counts
    cartCount.textContent = cartIds.length;
    cartCountHeader.textContent = cartIds.length;

    // Clear existing calendar blocks
    document.querySelectorAll('.cart-calendar-container .course-block').forEach(block => {
        block.remove();
    });
    
    // Clear course list
    if (cartCoursesList) {
        cartCoursesList.innerHTML = '';
    }

    if (cartIds.length > 0) {
        // Create URLSearchParams object properly
        const params = new URLSearchParams();
        cartIds.forEach(id => params.append('ids[]', id));

        fetch(`/cart-courses/?${params}`)
            .then(response => response.json())
            .then(data => {
                // Add simple list of courses
                if (cartCoursesList) {
                    const courseList = document.createElement('ul');
                    courseList.className = 'cart-courses-simple-list';
                    
                    data.courses.forEach(course => {
                        // Get the first section for professor info
                        const firstSection = Object.values(course.section_information)[0] || {};
                        
                        // Format meeting days for display
                        const meetingDays = [];
                        ['mon', 'tue', 'wed', 'thu', 'fri'].forEach(day => {
                            if (firstSection[`${day}_start_time`]) {
                                meetingDays.push(day.charAt(0).toUpperCase() + day.slice(1, 3));
                            }
                        });
                        
                        // Get a sample time to display
                        const sampleTime = firstSection.mon_start_time || 
                                           firstSection.tue_start_time || 
                                           firstSection.wed_start_time || 
                                           firstSection.thu_start_time || 
                                           firstSection.fri_start_time || 'TBD';
                        
                        const courseItem = document.createElement('div');
                        courseItem.innerHTML = `
                            <div class="course-card cart-course-card">
                                <div class="course-card-columns">
                                    <div class="course-card-left">
                                        <div class="course-code">
                                            ${Array.isArray(course.course_acronyms) 
                                                ? course.course_acronyms.map(acronym => `<div>${acronym}</div>`).join('')
                                                : `<div>${course.course_acronyms}</div>`}
                                        </div>
                                    </div>
                                    <div class="course-card-right">
                                        <span class="info-text">Professor ${firstSection.professor_name || "TBA"} | ${meetingDays.join(', ')} ${sampleTime}</span>
                                        <h4 class="course-name">${course.name}</h4>
                                    </div>
                                    <button onclick="toggleCart('${course.id}')" class="remove-btn">×</button>
                                </div>
                            </div>
                        `;
                        courseList.appendChild(courseItem);
                    });
                    
                    cartCoursesList.appendChild(courseList);
                }
                
                // Continue with the existing calendar code
                const timeSlotCourses = {};
                
                // Group courses by time slot
                data.courses.forEach(course => {
                    Object.values(course.section_information).forEach(section => {
                        const days = ['mon', 'tue', 'wed', 'thu', 'fri'];
                        days.forEach(day => {
                            const startTime = section[`${day}_start_time`];
                            const endTime = section[`${day}_end_time`];
                            
                            if (startTime && endTime) {
                                // Parse time format
                                const startTimeParts = startTime.match(/(\d+):(\d+)\s*(AM|PM)/i);
                                if (!startTimeParts) {
                                    console.error(`Invalid time format: ${startTime}`);
                                    return;
                                }
                                
                                let startHour = parseInt(startTimeParts[1]);
                                const startMinutes = parseInt(startTimeParts[2]);
                                const period = startTimeParts[3].toUpperCase();
                                
                                // Convert to 24-hour format
                                if (period === 'PM' && startHour < 12) {
                                    startHour += 12;
                                } else if (period === 'AM' && startHour === 12) {
                                    startHour = 0;
                                }
                                
                                // Create a key for this time slot
                                const timeSlotKey = `${day}-${startHour}`;
                                
                                // Initialize array for this slot if needed
                                if (!timeSlotCourses[timeSlotKey]) {
                                    timeSlotCourses[timeSlotKey] = [];
                                }
                                
                                // Calculate duration
                                const start = new Date(`2000/01/01 ${startTime}`);
                                const end = new Date(`2000/01/01 ${endTime}`);
                                const duration = (end - start) / 1000 / 60; // duration in minutes
                                
                                // Store course data for this slot
                                timeSlotCourses[timeSlotKey].push({
                                    course,
                                    section,
                                    startHour,
                                    startMinutes,
                                    duration,
                                    startTime,
                                    endTime
                                });
                            }
                        });
                    });
                });
                
                // Now render courses with appropriate widths
                Object.entries(timeSlotCourses).forEach(([slotKey, coursesInSlot]) => {
                    const [day, hour] = slotKey.split('-');
                    
                    // Get the time slot element
                    const timeSlot = document.querySelector(
                        `.cart-calendar-container .time-slot[data-hour="${hour}"][data-day="${day}"]`
                    );
                    
                    if (!timeSlot) {
                        console.error(`No time slot found for ${day} at hour ${hour}`);
                        return;
                    }
                    
                    // Calculate width and position for each course
                    const courseCount = coursesInSlot.length;
                    const width = 100 / courseCount;
                    
                    // Render each course with calculated width and position
                    coursesInSlot.forEach((courseData, index) => {
                        const { course, section, startMinutes, duration, startTime, endTime } = courseData;
                        
                        // Create course block
                        const block = document.createElement('div');
                        block.className = 'course-block';
                        block.style.height = `${duration}px`;
                        block.style.top = `${startMinutes}px`;
                        
                        // Set width and position for overlapping handling
                        block.style.width = `${width}%`;
                        block.style.left = `${index * width}%`;
                        
                        // Set different colors for each course
                        const colors = ['#e1d7f1', '#d1e7f7', '#fde2d4', '#d4e5d4', '#f7d1e3'];
                        block.style.backgroundColor = colors[index % colors.length];
                        
                        // Add course information
                        block.innerHTML = `
                            <div class="course-acronyms">
                                ${course.course_acronyms.map(code => `<div>${code}</div>`).join('')}
                            </div>
                            <div class="course-time">${startTime} - ${endTime}</div>
                            <div class="course-location">${section.course_location || 'TBA'}</div>
                        `;
                        
                        timeSlot.appendChild(block);
                    });
                });
            })
            .catch(error => {
                console.error('Error updating cart display:', error);
            });
    }
}

function resetCart() {
    localStorage.removeItem('courseCart');
    localStorage.removeItem('courseTimeConflicts');
    
    updateCartDisplay();
    
    // Reset all button states
    document.querySelectorAll('.cart-button').forEach(button => {
        const icon = button.querySelector('i');
        icon.className = 'fa-solid fa-plus';
        button.classList.remove('in-cart');
    });
    
    // Clear all conflict styling
    document.querySelectorAll('.course-card').forEach(card => {
        card.classList.remove('time-conflict');
        card.style.border = '';
        card.style.backgroundColor = '';
        
        const existingBadge = card.querySelector('.conflict-badge');
        if (existingBadge) existingBadge.remove();
    });
}
