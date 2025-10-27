const CODE_TO_NAME = JSON.parse(document.getElementById('dept-dict').textContent);

let globalCourseList = [];
const TIMEOUT_MS = 3000;
let tooltipElement = null;

// Initialize tooltip element
function initTooltip() {
    if (!tooltipElement) {
        tooltipElement = document.createElement('div');
        tooltipElement.className = 'custom-tooltip';
        document.body.appendChild(tooltipElement);
    }
}

// Show tooltip
function showTooltip(button, text) {
    initTooltip();
    const rect = button.getBoundingClientRect();
    tooltipElement.textContent = text;
    tooltipElement.style.left = rect.left + (rect.width / 2) - (tooltipElement.offsetWidth / 2) + 'px';
    tooltipElement.style.top = rect.top - tooltipElement.offsetHeight - 10 + 'px';
    tooltipElement.classList.add('show');
}

// Hide tooltip
function hideTooltip() {
    if (tooltipElement) {
        tooltipElement.classList.remove('show');
    }
}

// Prevents rapid-fire execution of a function by waiting for a pause in calls
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

// Handles adding/removing courses from the cart and updates UI accordingly
function handleCartClick(event, courseId, sectionId) {
    event.stopPropagation();  // Prevent event bubbling to parent elements
    
    // Get current cart state from localStorage
    let cart = JSON.parse(localStorage.getItem('courseCart') || '[]');
    let cartItem = cart.find(item => item.courseId === courseId && item.sectionId === sectionId);
    
    // Add or remove course from cart based on current state
    if (!cartItem) {
        cart.push({
            courseId: courseId,
            sectionId: sectionId
        });
        updateButtonState(courseId, true);
    } else {
        // Remove course and update UI if it was the last section
        cart = cart.filter(item => item.courseId !== courseId || item.sectionId !== sectionId);
        let containsCourse = cart.filter(item => item.courseId === courseId);
        if (containsCourse.length === 0) {
            updateButtonState(courseId, false);
        }
    }
    
    // Save updated cart and refresh displays
    localStorage.setItem('courseCart', JSON.stringify(cart));
    updateCartDisplay();
    findAndMarkAllCartConflicts();
}

function toggleCartPanel() {
    const panel = document.getElementById('cart-side-panel');
    const mainContent = document.querySelector('.main-content');
    const courseContainer = document.querySelector('.course-container');
    
    if (panel.classList.contains('open')) {
        // Closing panel with animation sequence
        courseContainer.style.opacity = '0';
        courseContainer.classList.add('hidden');
        panel.classList.add('closing');
        
        // Handle panel closing animation
        setTimeout(() => {
            panel.classList.remove('open', 'closing');
            mainContent.classList.remove('shifted');
            courseContainer.classList.remove('shifted');
            
            // Fade content back in
            setTimeout(() => {
                courseContainer.classList.add('fade-in');
                courseContainer.classList.remove('hidden');
                courseContainer.style.opacity = '1';
                
                setTimeout(() => {
                    courseContainer.classList.remove('fade-in');
                }, 300);
            }, 100);
        }, 300);
    } else {
        // Opening panel
        panel.classList.add('open');
        mainContent.classList.add('shifted');
        courseContainer.classList.add('shifted');
        updateCartDisplay();
    }
}

// Removes all conflict and warning styling from course cards
function clearConflictStyling() {
    return new Promise(resolve => {
        // Get all course cards and track completion
        const cards = Array.from(document.querySelectorAll('.course-card'));
        let completed = 0;
        
        cards.forEach(card => {
            requestAnimationFrame(() => {
                // Remove styling classes and inline styles
                card.classList.remove('time-conflict', 'time-warning');
                card.style.border = '';
                card.style.backgroundColor = '';
                
                // Remove conflict and warning badges with timeout protection
                let existingBadge = card.querySelector('.conflict-badge');
                let warningBadge = card.querySelector('.warning-badge');
                let startTime = Date.now();

                // Keep removing badges until none remain or timeout occurs
                while (existingBadge || warningBadge) {
                    if (Date.now() - startTime > TIMEOUT_MS) {
                        console.error('Timeout removing badges');
                        break;
                    }
                    if (existingBadge) {
                        card.removeChild(existingBadge);
                        existingBadge = card.querySelector('.conflict-badge');
                    }
                    if (warningBadge) {
                        card.removeChild(warningBadge);
                        warningBadge = card.querySelector('.warning-badge');
                    }
                }
                
                // Resolve promise when all cards are processed
                completed++;
                if (completed === cards.length) {
                    resolve();
                }
            });
        });
        
        // Handle empty card list case
        if (cards.length === 0) resolve();
    });
}

// Maps section meeting times from cart data into a structured format
function getCartCourseTimes(cartData) {
    // Convert each course's section times into structured meeting times
    return cartData.courses.map(cartCourse => {
        const cartSection = Object.values(cartCourse.section_information)[0];
        const meetingTimes = [];
        
        // Process each day of the week
        ['mon', 'tue', 'wed', 'thu', 'fri'].forEach(day => {
            if (cartSection[`${day}_start_time`] && cartSection[`${day}_end_time`]) {
                meetingTimes.push({
                    day,
                    start: new Date(`2000/01/01 ${cartSection[`${day}_start_time`]}`),
                    end: new Date(`2000/01/01 ${cartSection[`${day}_end_time`]}`),
                    courseId: cartCourse.id,
                    courseName: cartCourse.name
                });
            }
        });
        
        return {
            courseId: cartCourse.id,
            courseName: cartCourse.name,
            meetingTimes
        };
    }).filter(course => course.meetingTimes.length > 0); // Only include courses with actual meeting times
}

// Filters and returns course cards that aren't in the cart
function getNonCartCourseCards(cart) {
    return Array.from(document.querySelectorAll('.course-card')).filter(card => {
        const courseId = card.dataset.courseId;
        // Exclude cards that are in cart or marked as cart courses
        return courseId && 
               !cart.some(item => item.courseId === courseId) && 
               !card.classList.contains('cart-course-card');
    });
}

// Determines if two time periods overlap
function checkTimeConflict(start1, end1, start2, end2) {
    return !(end1 <= start2 || start1 >= end2);
}

// Applies visual styling to indicate a complete time conflict
function applyConflictStyling(card, cartCourseName) {
    // Add visual indicators for conflicts
    card.classList.add('time-conflict');
    card.style.border = '2px solid #ff817a';
    card.style.backgroundColor = 'rgba(255,0,0,0.07)';

    // Create and style the conflict badge
    const badge = document.createElement('div');
    badge.className = 'conflict-badge';
    badge.textContent = '⛔️ CONFLICT';
    badge.style.position = 'absolute';
    badge.style.top = '8px';
    badge.style.right = '50px';
    badge.style.backgroundColor = '#ff0000';
    badge.style.color = 'white';
    badge.style.padding = '3px 6px';
    badge.style.borderRadius = '3px';
    badge.style.fontSize = '12px';
    badge.style.fontWeight = 'bold';
    badge.style.zIndex = '100';
    badge.title = `All sections conflict with ${cartCourseName}`;

    // Ensure proper badge positioning
    if (getComputedStyle(card).position === 'static') {
        card.style.position = 'relative';
    }
    card.appendChild(badge);
}

// Applies visual styling to indicate a partial time conflict
function applyPartialConflictStyling(card, cartCourseName) {
    // Add visual indicators for partial conflicts
    card.classList.add('time-warning');
    card.style.border = '2px solid rgb(255, 176, 91)';
    card.style.backgroundColor = 'rgba(255, 176, 91, 0.1)';

    // Create and style the partial conflict badge
    const badge = document.createElement('div');
    badge.className = 'warning-badge';
    badge.textContent = '🔶 PARTIAL CONFLICT';
    badge.style.position = 'absolute';
    badge.style.top = '8px';
    badge.style.right = '50px';
    badge.style.backgroundColor = 'rgb(252, 130, 0)';
    badge.style.color = 'black';
    badge.style.padding = '3px 6px';
    badge.style.borderRadius = '3px';
    badge.style.fontSize = '12px';
    badge.style.fontWeight = 'bold';
    badge.style.zIndex = '100';
    badge.title = `Some sections conflict with ${cartCourseName}, but others are available`;

    // Ensure proper badge positioning
    if (getComputedStyle(card).position === 'static') {
        card.style.position = 'relative';
    }
    card.appendChild(badge);
}

// Checks which course-sections have conflicts with the cart and highlights course cards with conflicts
async function findAndMarkAllCartConflicts() {    
    // Initialize cart data and conflicts object
    const cart = JSON.parse(localStorage.getItem('courseCart') || '[]');
    const courseConflicts = {};
    
    // Clear any existing conflict styling before checking
    await clearConflictStyling();

    if (cart.length === 0) {
        localStorage.removeItem('courseTimeConflicts');
        return;
    }

    // Prepare cart data for API request
    const params = new URLSearchParams();
    params.append('cart', JSON.stringify(cart));
    
    try {
        // Fetch cart course details and process each course card
        const response = await fetch(`/cart-courses/?${params}`);
        const data = await response.json();
        const cartCourseTimes = getCartCourseTimes(data);
        const cards = getNonCartCourseCards(cart);
        
        // If no cart courses have meeting times, no conflicts are possible
        if (cartCourseTimes.length === 0) {
            localStorage.removeItem('courseTimeConflicts');
            return;
        }
        
        cards.forEach(card => {
            const courseId = card.dataset.courseId;
            // Skip courses with no time information
            if (card.dataset.sectionWithTime === 'TBD') {
                return null;
            }

            // Process section times for conflict checking
            let sectionTimes = card.dataset.sectionWithTime.split('|');
            let totalSections = 0;
            let conflictingSections = 0;

            // Parse and validate each section's time data
            sectionTimes = sectionTimes.map(section_time => {
                if (!section_time) {
                    console.warn('Empty section time encountered');
                    return null;
                }
                
                const section_time_split = section_time.split('~');
                if (section_time_split.length !== 2) {
                    console.warn(`Invalid section time format: ${section_time}`);
                    return null;
                }
                
                const [sectionNum, timeSlot] = section_time_split;
                if (!sectionNum || !timeSlot) {
                    console.warn(`Missing section number or time slot: ${section_time}`);
                    return null;
                }
                
                return {
                    sectionNumber: sectionNum.trim(),
                    timeSlot: timeSlot.trim()
                };
            }).filter(Boolean);
            
            // Track total valid sections for conflict ratio calculation
            totalSections = sectionTimes.length;
            
            // Check each section for time conflicts
            sectionTimes.forEach(section_time => {
                timeSlot = section_time.timeSlot;
                sectionNumber = section_time.sectionNumber;
                

                const timeMatch = timeSlot.match(/([MTWThF]+)\s+(\d{1,2}:\d{2}\s*(?:AM|PM)\s*-\s*\d{1,2}:\d{2}\s*(?:AM|PM))/i);
                if (!timeMatch) {
                    console.warn(`Invalid time format: ${timeSlot}`);
                    return;
                }

                const [_, daysString, timeRange] = timeMatch;
                const [startTime, endTime] = timeRange.split('-').map(t => t.trim());
                
                let hasConflict = false;
                const daysArray = daysString.match(/(?:Th)|[MTWF]/g) || [];

                // Check each day for conflicts
                daysArray.forEach(day => {
                    const dayMap = {
                        'M': 'mon',
                        'T': 'tue',
                        'W': 'wed',
                        'Th': 'thu',
                        'F': 'fri'
                    };
                    const shortDay = dayMap[day];
                    
                    if (shortDay) {
                        // Convert times to comparable format
                        const start = new Date(`2000/01/01 ${startTime}`);
                        const end = new Date(`2000/01/01 ${endTime}`);

                        
                        // Compare against each cart course's times
                        cartCourseTimes.forEach(cartCourse => {
                            cartCourse.meetingTimes.forEach(cartTime => {
                                if (cartTime.day === shortDay && 
                                    checkTimeConflict(start, end, cartTime.start, cartTime.end)) {
                                    hasConflict = true;
                                    
                                    // Track conflicts for later reference
                                    if (!courseConflicts[cartCourse.courseId]) {
                                        courseConflicts[cartCourse.courseId] = [];
                                    }
                                    
                                    // Add conflict if not already tracked for this section
                                    const existingConflict = courseConflicts[cartCourse.courseId]?.find(c => c.id === courseId);
                                    if (existingConflict) {
                                        // If this course already has conflicts, check if this section is already in the list
                                        if (!existingConflict.conflictingSections.includes(sectionNumber)) {
                                            existingConflict.conflictingSections.push(sectionNumber);
                                        }
                                    } else {
                                        // Create a new conflict entry for this course
                                        if (!courseConflicts[cartCourse.courseId]) {
                                            courseConflicts[cartCourse.courseId] = [];
                                        }
                                        courseConflicts[cartCourse.courseId].push({
                                            id: courseId,
                                            name: card.querySelector('.course-name')?.textContent || 'Unknown',
                                            conflictingSections: [sectionNumber]
                                        });
                                    }
                                }
                            });
                        });
                    }
                });
                
                if (hasConflict) {
                    conflictingSections++;
                }
            });
            
            // Apply appropriate styling based on conflict ratio
            if (conflictingSections > 0) {
                const conflictingCourseName = cartCourseTimes[0]?.courseName || 'another course';
                if (conflictingSections === totalSections) {
                    // All sections have conflicts
                    applyConflictStyling(card, conflictingCourseName);
                } else {
                    // Only some sections have conflicts
                    applyPartialConflictStyling(card, conflictingCourseName);
                }
            }
        });

        // Save conflicts for future reference
        localStorage.setItem('courseTimeConflicts', JSON.stringify(courseConflicts));
        
    } catch (error) {
        console.error('Error checking for conflicts:', error);
    }
}

// Updates the cart icon and styling for a course's add/remove button
function updateButtonState(courseId, inCart) {
    // Find and update all buttons for this course
    document.querySelectorAll(`.cart-button[data-course-id="${courseId}"]`).forEach(button => {
        const icon = button.querySelector('i');
        // Toggle button appearance based on cart state
        if (inCart) {
            icon.className = 'fa-solid fa-check';
            button.classList.add('in-cart');
            button.setAttribute('title', 'Course added to schedule - Click to view sections');
            button.setAttribute('aria-label', 'Course in schedule - Click to manage sections');
        } else {
            icon.className = 'fa-solid fa-plus';
            button.classList.remove('in-cart');
            button.setAttribute('title', 'Add course to schedule');
            button.setAttribute('aria-label', 'Add course to schedule');
        }
    });
}

// Handles the opening and closing of the course details side panel
function togglePanel(courseId = null) {
    const panel = document.getElementById('side-panel');
    const panelContent = document.getElementById('panel-content');
    const mainContent = document.querySelector('.main-content');
    const courseContainer = document.querySelector('.course-container');

    if (courseId) {
        // Opening panel with course details
        const clickedCard = document.querySelector(`.course-card[data-course-id="${courseId}"]`);
        panelContent.innerHTML = '<div class="loading">Loading...</div>';
        panel.classList.add('open');

        // Fetch and display course details
        fetch(`/details/${courseId}/`)  
            .then(response => {
                if (!response.ok) throw new Error(`Failed to load course details: ${response.status}`);
                return response.text();
            })
            .then(html => {
                // Reset scroll and update content
                panel.scrollTop = 0;
                panelContent.scrollTop = 0;
                panelContent.innerHTML = html;
                mainContent.classList.add('shifted');
                courseContainer.classList.add('shifted');

                // Scroll to show the clicked card
                if (clickedCard) {
                    clickedCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            })
            .catch(error => {
                console.error('Error:', error);
                panelContent.innerHTML = '<div class="error">Failed to load course details</div>';
            });
    } else {
        // Closing panel with animation sequence
        courseContainer.style.opacity = '0';
        courseContainer.classList.add('hidden');
        panel.classList.add('closing');

        // Remove active states from all cards
        document.querySelectorAll('.course-card').forEach(card => {
            card.classList.remove('active');
        });
        
        // Handle panel closing animation
        setTimeout(() => {
            panel.classList.remove('open', 'closing');
            mainContent.classList.remove('shifted');
            courseContainer.classList.remove('shifted');
            
            // Fade content back in
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

// Initializes course data by fetching details for all visible course cards
async function initializeCourses() {
    const courseCards = document.querySelectorAll('.course-card');
    
    // Fetch all courses in parallel
    await Promise.all(Array.from(courseCards).map(async (card, index) => {
        const courseId = card.dataset.courseId;
        const course = await getCourseById(courseId);
        if (course) {
            globalCourseList[index] = course;
        }
    }));
}

// Fetches detailed information for a specific course
async function getCourseById(courseId) {
    try {
        const response = await fetch(`/api/course/${courseId}/`);
        if (!response.ok) throw new Error('Course not found');
        const data = await response.json();
        return data.course;
    } catch (error) {
        console.error('Error fetching course:', error);
        return null;
    }
}

// Helper function to retrieve CSRF token from cookies
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        // Search for named cookie
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

// Updates the cart display with current courses and their calendar view
function updateCartDisplay() {
    // Get cart data and initialize display elements
    const cart = JSON.parse(localStorage.getItem('courseCart') || '[]');
    const cartCountHeader = document.getElementById('cart-count-header');
    const cartCredits = document.getElementById('cart-credits');
    const cartCoursesList = document.getElementById('cart-courses-list');
    
    // Update cart counters and clear existing content
    if (cartCountHeader) cartCountHeader.textContent = cart.length;
    if (cartCredits) cartCredits.textContent = '0';
    document.querySelectorAll('.cart-calendar-container .course-block').forEach(block => block.remove());
    if (cartCoursesList) cartCoursesList.innerHTML = '';

    // If cart has items, fetch and display course details
    if (cart.length > 0) {
        const params = new URLSearchParams();
        params.append('cart', JSON.stringify(cart));

        fetch(`/cart-courses/?${params}`)
            .then(response => response.json())
            .then(data => {
                // Calculate total credits
                let totalCredits = 0;
                data.courses.forEach(course => {
                    totalCredits += course.credits || 0;
                });
                if (cartCredits) {
                    cartCredits.textContent = totalCredits;
                }
                
                // Process each course for display
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
                                    <button onclick="handleCartClick(event, '${course.id}', '${Object.keys(course.section_information)[0]}')" class="remove-btn" title="Remove ${course.name} from schedule" aria-label="Remove ${course.name} from schedule">×</button>
                                </div>
                            </div>
                        `;
                    courseList.appendChild(courseItem);
                });
                    
                    cartCoursesList.appendChild(courseList);
                }
                
                // Generate and display calendar view
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
    // Clear cart data from storage
    localStorage.removeItem('courseCart');
    localStorage.removeItem('courseTimeConflicts');
    
    return new Promise(resolve => {
        // Reset all button states first
        const buttons = Array.from(document.querySelectorAll('.cart-button'));
        let completedButtons = 0;
        
        // Process each button in an animation frame
        buttons.forEach(button => {
            requestAnimationFrame(() => {
                const courseId = button.getAttribute('data-course-id');
                updateButtonState(courseId, false);
                
                // After all buttons are reset, clear conflict styling
                if (++completedButtons === buttons.length) {
                    clearConflictStyling().then(() => {
                        updateCartDisplay();
                        resolve();
                    });
                }
            });
        });
        
        // Handle empty button list
        if (buttons.length === 0) {
            updateCartDisplay();
            resolve();
        }
    });
}

// Export cart courses as CSV file for Workday
async function exportCart() {
    const cart = JSON.parse(localStorage.getItem('courseCart') || '[]');
    
    if (cart.length === 0) {
        alert('Your schedule is empty. Add courses to export.');
        return;
    }
    
    try {
        // Fetch course details for all cart items
        const response = await fetch(`/cart-courses/?cart=${encodeURIComponent(JSON.stringify(cart))}`);
        const data = await response.json();
        
        if (!data.courses || data.courses.length === 0) {
            alert('No course data found.');
            return;
        }
        
        // Generate RSS feed content
        const now = new Date().toUTCString();
        let rssContent = '<?xml version="1.0" encoding="UTF-8"?>\n';
        rssContent += '<rss version="2.0" xmlns:workday="http://www.workday.com/namespace">\n';
        rssContent += '  <channel>\n';
        rssContent += '    <title>Amherst College Course Schedule</title>\n';
        rssContent += '    <link>https://www.amherst.edu</link>\n';
        rssContent += '    <description>Student course schedule export from Amherst College Course Catalog</description>\n';
        rssContent += `    <pubDate>${now}</pubDate>\n`;
        rssContent += '    <generator>Amherst Course Catalog</generator>\n\n';
        
        // Add each course as an RSS item
        data.courses.forEach(course => {
            // Get course code (first one if multiple)
            const courseCode = course.course_acronyms && course.course_acronyms.length > 0 
                ? course.course_acronyms[0] 
                : 'N/A';
            
            // Extract department from course code (e.g., "COSC-111" -> "COSC")
            const department = courseCode.split('-')[0] || 'N/A';
            
            // Get course name and escape XML special characters
            const courseName = escapeXml(course.name || 'N/A');
            
            // Get section information
            const sectionInfo = course.section_information || {};
            const sectionNumber = Object.keys(sectionInfo)[0] || 'N/A';
            const credits = course.credits || 4;
            
            // Create RSS item for course
            rssContent += '    <item>\n';
            rssContent += `      <title>${courseCode}: ${courseName}</title>\n`;
            rssContent += `      <description><![CDATA[\n`;
            rssContent += `        <strong>Course:</strong> ${courseName}<br/>\n`;
            rssContent += `        <strong>Course Code:</strong> ${courseCode}<br/>\n`;
            rssContent += `        <strong>Department:</strong> ${department}<br/>\n`;
            rssContent += `        <strong>Section:</strong> ${sectionNumber}<br/>\n`;
            rssContent += `        <strong>Credits:</strong> ${credits}\n`;
            rssContent += `      ]]></description>\n`;
            rssContent += `      <guid isPermaLink="false">amherst-course-${course.id}-section-${sectionNumber}</guid>\n`;
            rssContent += `      <pubDate>${now}</pubDate>\n`;
            
            // Add Workday-specific custom elements
            rssContent += `      <workday:courseCode>${escapeXml(courseCode)}</workday:courseCode>\n`;
            rssContent += `      <workday:courseName>${courseName}</workday:courseName>\n`;
            rssContent += `      <workday:department>${escapeXml(department)}</workday:department>\n`;
            rssContent += `      <workday:section>${escapeXml(sectionNumber)}</workday:section>\n`;
            rssContent += `      <workday:credits>${credits}</workday:credits>\n`;
            
            rssContent += '    </item>\n\n';
        });
        
        rssContent += '  </channel>\n';
        rssContent += '</rss>';
        
        // Create and download file
        const blob = new Blob([rssContent], { type: 'application/rss+xml;charset=utf-8' });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'amherst-schedule.rss';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        
    } catch (error) {
        console.error('Error exporting schedule:', error);
        alert('Failed to export schedule. Please try again.');
    }
}

// Helper function to escape XML special characters
function escapeXml(unsafe) {
    if (!unsafe) return '';
    return unsafe.toString()
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&apos;');
}

// Displays modal with section options for a course
function showSectionModal(event, courseId, courseName) {
    event.stopPropagation();
    const modal = document.getElementById('section-modal');
    const sectionList = document.getElementById('section-list');
    
    // Get stored conflicts and cart data
    const courseConflicts = JSON.parse(localStorage.getItem('courseTimeConflicts') || '{}');
    const cart = JSON.parse(localStorage.getItem('courseCart') || '[]');

    // Fetch and display sections
    fetch(`/api/course/${courseId}/sections/`)
        .then(response => response.json())
        .then(sections => {
            sectionList.innerHTML = '';
            
            sections.forEach(section => {
                // Create section element with appropriate styling
                const sectionElement = document.createElement('div');
                sectionElement.className = 'section-item';

                // Check if this section is in the cart
                const isInCart = cart.some(item => 
                    item.courseId === courseId && 
                    item.sectionId === section.section_number
                );

                // Check if this section is in conflicts
                let hasConflict = false;
                Object.values(courseConflicts).forEach(conflicts => {

                    conflicts.forEach(conflict => {
                        if (conflict.conflictingSections && 
                            conflict.id === courseId &&
                            conflict.conflictingSections.includes(section.section_number)) {
                            hasConflict = true;
                        }
                    });
                });
                
                // Add conflict styling if needed
                if (isInCart) {
                    sectionElement.classList.add('section-in-cart');
                } else if (hasConflict) {
                    sectionElement.classList.add('section-conflict');
                }
                
                sectionElement.innerHTML = `
                    <div class="section-header">
                        <span>Section ${section.section_number}</span>
                        ${isInCart ? '<span class="cart-badge">✓ In Cart</span>' : ''}
                        ${hasConflict ? '<span class="conflict-badge">⛔️ Conflict</span>' : ''}
                    </div>
                    <div class="section-details">
                        <p><strong>Professor:</strong> ${section.professor_name || 'TBA'}</p>
                        <p><strong>Location:</strong> ${section.location || 'TBA'}</p>
                        <p><strong>Time:</strong> ${formatMeetingTimes(section) || 'TBD'}</p>
                    </div>
                `;
                
                sectionElement.onclick = (clickEvent) => {
                    clickEvent.stopPropagation();
                    handleCartClick(clickEvent, courseId, section.section_number);
                    modal.style.display = 'none';
                };
                sectionList.appendChild(sectionElement);
            });
        });
    
    modal.style.display = 'block';
}

// Formats meeting times for display in the section modal
function formatMeetingTimes(section) {
    const days = [
        {day: 'monday', short: 'Mon'},
        {day: 'tuesday', short: 'Tue'},
        {day: 'wednesday', short: 'Wed'},
        {day: 'thursday', short: 'Thu'},
        {day: 'friday', short: 'Fri'}
    ];
    
    // Build array of formatted meeting times
    let times = days
        .filter(({day}) => section[`${day}_start_time`] && section[`${day}_end_time`])
        .map(({day, short}) => 
            `${short} ${section[`${day}_start_time`]}-${section[`${day}_end_time`]}`
        );
    
    return times.join(', ');
}

let currentPage = 1;
let isLoading = false;

async function loadPage(pageNumber) {
    if (isLoading) return;
    isLoading = true;

    try {
        // Show loading state
        document.querySelector('.course-container').style.opacity = '0.5';
        
        // Get current search query if any
        const searchParams = new URLSearchParams(window.location.search);
        const searchQuery = searchParams.get('search') || '';
        
        // Build URL with page and search parameters
        const url = `/?page=${pageNumber}${searchQuery ? `&search=${searchQuery}` : ''}`;
        
        // Fetch new page content
        const response = await fetch(url);
        const html = await response.text();
        
        // Parse the new HTML
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Update the course container
        const courseContainer = document.querySelector('.course-container');
        const newCourses = doc.querySelector('.course-container');
        courseContainer.innerHTML = newCourses.innerHTML;

        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.value = searchQuery;
        }
        
        // Update pagination controls
        updatePaginationControls(pageNumber);
        
        // Update URL without refresh
        window.history.pushState({}, '', url);
        currentPage = pageNumber;
        
        // Reinitialize course functionality
        await initializeCourses();
        
        // Update button states for courses in cart
        const cart = JSON.parse(localStorage.getItem('courseCart') || '[]');
        cart.forEach(item => {
            updateButtonState(item.courseId, true);
        });
        
        // Check for conflicts after updating button states
        await findAndMarkAllCartConflicts();
        
        // Restore opacity
        courseContainer.style.opacity = '1';
        
        // Bind events to new elements
        bindCourseEvents();
        
    } catch (error) {
        console.error('Error loading page:', error);
    } finally {
        isLoading = false;
    }
}

function updatePaginationControls(pageNumber) {
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    const pageInfo = document.querySelector('.page-info');
    const totalPages = parseInt(document.querySelector('.pagination-controls').dataset.totalPages);
    
    prevBtn.disabled = pageNumber <= 1;
    nextBtn.disabled = pageNumber >= totalPages;
    pageInfo.textContent = `Page ${pageNumber} of ${totalPages}`;
}

function bindCourseEvents() {
    // Rebind click handlers for course cards
    document.querySelectorAll('.course-card').forEach(card => {
        card.addEventListener('click', function(event) {
            if (!event.target.closest('.cart-button')) {
                document.querySelectorAll('.course-card').forEach(c => {
                    c.classList.remove('active');
                });
                this.classList.add('active');
                const courseId = this.dataset.courseId;
                togglePanel(courseId);
            }
        });
    });
    
    // Add tooltip handlers to cart buttons
    document.querySelectorAll('.cart-button').forEach(button => {
        button.addEventListener('mouseenter', function() {
            const title = this.getAttribute('title');
            if (title) {
                showTooltip(this, title);
            }
        });
        
        button.addEventListener('mouseleave', function() {
            hideTooltip();
        });
    });
}

// ============================================================================
// AI ADVISOR FUNCTIONS
// ============================================================================

/**
 * Format markdown-style text to HTML
 * @param {string} text - Text with markdown formatting
 * @returns {string} HTML string
 */
function formatMarkdownToHTML(text) {
    // Split into lines for processing
    const lines = text.split('\n');
    const formatted = [];
    let inList = false;
    let listType = 'ul'; // Track if we're in ul or ol
    
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        
        // Skip empty lines but add spacing
        if (line === '') {
            if (inList) {
                formatted.push(`</${listType}>`);
                inList = false;
            }
            formatted.push('<br>');
            continue;
        }
        
        // Handle headers (##, ###) - must come before bold conversion
        if (line.startsWith('###')) {
            if (inList) {
                formatted.push(`</${listType}>`);
                inList = false;
            }
            line = line.replace(/^###\s+/, '');
            // Convert any **text** to <strong>
            line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
            formatted.push(`<h4>${line}</h4>`);
            continue;
        }
        else if (line.startsWith('##')) {
            if (inList) {
                formatted.push(`</${listType}>`);
                inList = false;
            }
            line = line.replace(/^##\s+/, '');
            // Convert any **text** to <strong>
            line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
            formatted.push(`<h3>${line}</h3>`);
            continue;
        }
        
        // Check if line is a standalone bold header (e.g., "**Prerequisites:**")
        const boldHeaderMatch = line.match(/^\*\*([^*]+):\*\*\s*$/);
        if (boldHeaderMatch) {
            if (inList) {
                formatted.push(`</${listType}>`);
                inList = false;
            }
            formatted.push(`<h3>${boldHeaderMatch[1]}:</h3>`);
            continue;
        }
        
        // Handle bullet points (*, -, •)
        if (line.match(/^[\*\-•]\s+/)) {
            if (!inList || listType !== 'ul') {
                if (inList) formatted.push(`</${listType}>`);
                formatted.push('<ul>');
                inList = true;
                listType = 'ul';
            }
            line = line.replace(/^[\*\-•]\s+/, '');
            // Convert **bold** and *italic*
            line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
            line = line.replace(/\*([^*]+?)\*/g, '<em>$1</em>');
            formatted.push(`<li>${line}</li>`);
            continue;
        }
        
        // Handle numbered lists
        if (line.match(/^\d+\.\s+/)) {
            if (!inList || listType !== 'ol') {
                if (inList) formatted.push(`</${listType}>`);
                formatted.push('<ol>');
                inList = true;
                listType = 'ol';
            }
            line = line.replace(/^\d+\.\s+/, '');
            // Convert **bold** and *italic*
            line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
            line = line.replace(/\*([^*]+?)\*/g, '<em>$1</em>');
            formatted.push(`<li>${line}</li>`);
            continue;
        }
        
        // Regular paragraph
        if (inList) {
            formatted.push(`</${listType}>`);
            inList = false;
        }
        
        // Convert **bold** and *italic* in paragraphs
        line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        line = line.replace(/\*([^*]+?)\*/g, '<em>$1</em>');
        formatted.push(`<p>${line}</p>`);
    }
    
    // Close any open list
    if (inList) {
        formatted.push(`</${listType}>`);
    }
    
    return formatted.join('');
}

/**
 * Toggle the AI advisor panel open/closed
 */
function toggleAdvisorPanel() {
    const panel = document.getElementById('ai-advisor-panel');
    const isOpening = !panel.classList.contains('open');
    
    panel.classList.toggle('open');
    
    // Auto-analyze on first open if cart has courses
    if (isOpening) {
        const cart = JSON.parse(localStorage.getItem('courseCart') || '[]');
        const messagesContainer = document.getElementById('advisor-messages');
        
        // Only auto-analyze if cart has courses and no messages yet
        if (cart.length > 0 && messagesContainer.children.length === 0) {
            setTimeout(() => {
                askAdvisor('Analyze my current schedule and suggest improvements');
            }, 300);
        } else if (cart.length === 0 && messagesContainer.children.length === 0) {
            // Show welcome message if cart is empty
            addAdvisorMessage(
                "👋 Welcome! Add some courses to your schedule and I'll help you analyze it and suggest complementary courses.",
                'assistant'
            );
        }
    }
}

/**
 * Ask the AI advisor a question
 * @param {string} question - Optional predefined question
 */
async function askAdvisor(question = null) {
    const input = document.getElementById('advisor-question');
    const query = question || input.value.trim();
    
    if (!query) return;
    
    // Clear input if user typed it
    if (!question) input.value = '';
    
    // Add user message to chat
    addAdvisorMessage(query, 'user');
    
    // Show loading message
    const loadingId = addAdvisorMessage('🤔 Thinking...', 'assistant', true);
    
    try {
        // Get cart data
        const cart = JSON.parse(localStorage.getItem('courseCart') || '[]');
        
        if (cart.length === 0 && !query.toLowerCase().includes('suggest')) {
            removeLoadingMessage(loadingId);
            addAdvisorMessage(
                "Your schedule is empty! Add some courses first, or ask me to suggest courses to get started.",
                'assistant'
            );
            return;
        }
        
        // Call backend API
        const params = new URLSearchParams({
            cart: JSON.stringify(cart),
            question: query
        });
        
        const response = await fetch(`/api/advisor/?${params}`);
        const data = await response.json();
        
        // Remove loading message
        removeLoadingMessage(loadingId);
        
        if (data.success) {
            // Display AI response
            displayAdvisorResponse(data);
        } else {
            addAdvisorMessage(
                `❌ Error: ${data.error || 'Failed to get advice'}`,
                'assistant'
            );
        }
        
    } catch (error) {
        removeLoadingMessage(loadingId);
        addAdvisorMessage(
            '❌ Sorry, I encountered an error. Please try again or check your internet connection.',
            'assistant'
        );
        console.error('Advisor error:', error);
    }
}

/**
 * Add a message to the advisor chat
 * @param {string} text - Message text
 * @param {string} sender - 'user' or 'assistant'
 * @param {boolean} isLoading - Whether this is a loading message
 * @returns {string} Message ID
 */
function addAdvisorMessage(text, sender, isLoading = false) {
    const container = document.getElementById('advisor-messages');
    const messageDiv = document.createElement('div');
    const messageId = `msg-${Date.now()}-${Math.random()}`;
    
    messageDiv.id = messageId;
    messageDiv.className = `advisor-message ${sender} ${isLoading ? 'loading' : ''}`;
    
    // Format assistant messages with markdown, keep user messages as plain text
    if (sender === 'assistant' && !isLoading) {
        messageDiv.innerHTML = formatMarkdownToHTML(text);
    } else {
        messageDiv.textContent = text;
    }
    
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
    
    return messageId;
}

/**
 * Display the full advisor response with recommendations
 * @param {object} data - Response data from API
 */
function displayAdvisorResponse(data) {
    // Display main advice
    addAdvisorMessage(data.advice, 'assistant');
    
    // Display recommendations as interactive cards
    if (data.recommendations && data.recommendations.length > 0) {
        const container = document.getElementById('advisor-messages');
        const recsDiv = document.createElement('div');
        recsDiv.className = 'advisor-recommendations';
        
        data.recommendations.forEach(rec => {
            const card = createRecommendationCard(rec);
            recsDiv.appendChild(card);
        });
        
        container.appendChild(recsDiv);
        container.scrollTop = container.scrollHeight;
    }
}

/**
 * Create a recommendation card element
 * @param {object} course - Course recommendation data
 * @returns {HTMLElement} Card element
 */
function createRecommendationCard(course) {
    const card = document.createElement('div');
    card.className = 'recommendation-card';
    
    const deptBadges = course.departments
        .map(dept => `<span class="dept-badge">${dept}</span>`)
        .join(' ');
    
    card.innerHTML = `
        <div class="rec-header">
            <strong>${course.code}</strong>
            <span class="rec-credits">${course.credits} credits</span>
        </div>
        <div class="rec-title">${course.name}</div>
        <div class="rec-departments">${deptBadges}</div>
        <div class="rec-reason">${course.reason}</div>
        <button onclick="togglePanel(${course.id})" class="rec-view-btn">
            <i class="fa-solid fa-eye"></i> View Details
        </button>
    `;
    
    return card;
}

/**
 * Remove a loading message by ID
 * @param {string} messageId - ID of message to remove
 */
function removeLoadingMessage(messageId) {
    const message = document.getElementById(messageId);
    if (message) {
        message.remove();
    }
}

