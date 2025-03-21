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

/* Add this to your script section */
function handleCartClick(event, courseId, sectionId) {
    event.stopPropagation();  // Prevent event from bubbling up to course-card
    
    let cart = JSON.parse(localStorage.getItem('courseCart') || '[]');
    let cartItem = cart.find(item => item.courseId === courseId );
    
    if (!cartItem) {
        cart.push({
            courseId: courseId,
            sectionId: sectionId
        });
        updateButtonState(courseId, true);
    } else {
        cart = cart.filter(item => item.courseId !== courseId);
        updateButtonState(courseId, false);
    }
    
    localStorage.setItem('courseCart', JSON.stringify(cart));
    updateCartDisplay();
    findAndMarkAllCartConflicts();
}

function toggleCartPanel() {
    const panel = document.getElementById('cart-side-panel');
    panel.classList.toggle('open');
    updateCartDisplay();
}

// Find courses with same meeting time and apply styling
function findAndMarkAllCartConflicts() {    
    const cart = JSON.parse(localStorage.getItem('courseCart') || '[]');
    
    // Clear existing conflict styling
    document.querySelectorAll('.course-card').forEach(card => {
        card.classList.remove('time-conflict');
        card.style.border = '';
        card.style.backgroundColor = '';
        const existingBadge = card.querySelector('.conflict-badge');
        if (existingBadge) existingBadge.remove();
    });
    
    if (cart.length === 0) {
        localStorage.removeItem('courseTimeConflicts');
        return;
    }
    
    const params = new URLSearchParams();
    params.append('cart', JSON.stringify(cart));
    
    fetch(`/cart-courses/?${params}`)
        .then(response => response.json())
        .then(data => {
            const courseConflicts = {};
            
            data.courses.forEach(cartCourse => {
                const cartSection = Object.values(cartCourse.section_information)[0];
                const cartCourseId = cartCourse.id;
                const cartCourseName = cartCourse.name;
                
                // Get meeting times for cart section
                const cartMeetingTimes = [];
                ['mon', 'tue', 'wed', 'thu', 'fri'].forEach(day => {
                    if (cartSection[`${day}_start_time`] && cartSection[`${day}_end_time`]) {
                        cartMeetingTimes.push({
                            day,
                            start: new Date(`2000/01/01 ${cartSection[`${day}_start_time`]}`),
                            end: new Date(`2000/01/01 ${cartSection[`${day}_end_time`]}`)
                        });
                    }
                });

                // Check visible course cards for conflicts
                document.querySelectorAll('.course-card').forEach(card => {
                    const courseId = card.dataset.courseId;
                    if (cart.some(item => item.courseId === courseId)) return;

                    const sectionModal = document.createElement('div');
                    sectionModal.style.display = 'none';
                    document.body.appendChild(sectionModal);

                    fetch(`/api/course/${courseId}/sections/`)
                        .then(response => response.json())
                        .then(sections => {
                            let hasConflict = false;
                            
                            sections.forEach(section => {
                                ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'].forEach(day => {
                                    const shortDay = day.substring(0, 3);
                                    if (section[`${day}_start_time`] && section[`${day}_end_time`]) {
                                        const start = new Date(`2000/01/01 ${section[`${day}_start_time`]}`);
                                        const end = new Date(`2000/01/01 ${section[`${day}_end_time`]}`);
                                        
                                        cartMeetingTimes.forEach(cartTime => {
                                            if (cartTime.day === shortDay && 
                                                !(end <= cartTime.start || start >= cartTime.end)) {
                                                hasConflict = true;
                                            }
                                        });
                                    }
                                });
                            });

                            if (hasConflict) {
                                const courseName = card.querySelector('.course-name')?.textContent || 'Unknown';
                                
                                if (!courseConflicts[cartCourseId]) {
                                    courseConflicts[cartCourseId] = [];
                                }
                                courseConflicts[cartCourseId].push({
                                    id: courseId,
                                    name: courseName
                                });

                                card.classList.add('time-conflict');
                                card.style.border = '2px solid #ff817a';
                                card.style.backgroundColor = 'rgba(255,0,0,0.07)';

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

                                if (getComputedStyle(card).position === 'static') {
                                    card.style.position = 'relative';
                                }
                                
                                card.appendChild(badge);
                            }
                        });
                });
            });

            localStorage.setItem('courseTimeConflicts', JSON.stringify(courseConflicts));
        })
        .catch(error => {
            console.error('Error checking conflicts:', error);
        });
}

// Update your conflict highlighting function to use the stored conflicts
function highlightTimeConflicts() {
    findAndMarkAllCartConflicts();

    // Get courses in cart with new format
    const cart = JSON.parse(localStorage.getItem('courseCart') || '[]');
    
    // Reset all course cards first
    document.querySelectorAll('.course-card').forEach(card => {
        card.classList.remove('time-conflict');
        card.style.border = '';
        
        const existingBadge = card.querySelector('.conflict-badge');
        if (existingBadge) existingBadge.remove();
    });
    
    if (cart.length === 0) return;
    
    // Get stored conflicts
    const courseConflicts = JSON.parse(localStorage.getItem('courseTimeConflicts') || '{}');
    
    // Check each course card for conflicts with cart courses
    document.querySelectorAll('.course-card').forEach(card => {
        const courseId = card.dataset.courseId;
        
        // Skip courses already in cart using new format
        if (cart.some(item => item.courseId === courseId)) return;
        
        // Check if any cart course conflicts with this course
        let hasConflict = false;
        
        cart.forEach(cartItem => {
            // Check if this cart course has conflicts with the current card
            if (courseConflicts[cartItem.courseId] && 
                courseConflicts[cartItem.courseId].includes(courseId)) {
                hasConflict = true;
            }
        });
        
        if (hasConflict) {
            card.classList.add('time-conflict');
        }
    });
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
    const cart = JSON.parse(localStorage.getItem('courseCart') || '[]');
    const cartCount = document.getElementById('cart-count');
    const cartCountHeader = document.getElementById('cart-count-header');
    const cartCoursesList = document.getElementById('cart-courses-list');
    
    // Update counts
    cartCount.textContent = cart.length;
    cartCountHeader.textContent = cart.length;

    // Clear existing calendar blocks
    document.querySelectorAll('.cart-calendar-container .course-block').forEach(block => {
        block.remove();
    });
    
    // Clear course list
    if (cartCoursesList) {
        cartCoursesList.innerHTML = '';
    }

    if (cart.length > 0) {
        // Create URLSearchParams object properly
        const params = new URLSearchParams();
        params.append('cart', JSON.stringify(cart));

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
                                    <button onclick="handleCartClick(event, '${course.id}', '${Object.values(course.section_information)[0].id}')" class="remove-btn">×</button>
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

function showSectionModal(event, courseId, courseName) {
    event.stopPropagation();
    const modal = document.getElementById('section-modal');
    const sectionList = document.getElementById('section-list');
    
    // Fetch sections for this course
    fetch(`/api/course/${courseId}/sections/`)
        .then(response => response.json())
        .then(sections => {
            sectionList.innerHTML = ''; // Clear existing sections
            
            sections.forEach(section => {
                const sectionElement = document.createElement('div');
                sectionElement.className = 'section-item';
                sectionElement.innerHTML = `
                    Section ${section.section_number}<br>
                    Professor: ${section.professor_name}<br>
                    Location: ${section.location}<br>
                    Time: ${formatMeetingTimes(section)}
                `;
                sectionElement.onclick = () => {
                    handleCartClick(event, courseId, section.id);
                    modal.style.display = 'none';
                };
                sectionList.appendChild(sectionElement);
            });
        });
    
    modal.style.display = 'block';
}

function formatMeetingTimes(section) {
    const days = [
        {day: 'monday', short: 'Mon'},
        {day: 'tuesday', short: 'Tue'},
        {day: 'wednesday', short: 'Wed'},
        {day: 'thursday', short: 'Thu'},
        {day: 'friday', short: 'Fri'}
    ];
    
    let times = [];
    days.forEach(({day, short}) => {
        if (section[`${day}_start_time`] && section[`${day}_end_time`]) {
            times.push(`${short} ${section[`${day}_start_time`]}-${section[`${day}_end_time`]}`);
        }
    });
    
    return times.join(', ');
}
