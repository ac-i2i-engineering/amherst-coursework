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

// Create debounced version of search_filter
const debouncedSearch = debounce((query, threshold) => {
    search_filter(query, threshold);
}, 400); // 400ms delay

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

function toggleCart(courseId) {
    // Get existing cart or initialize empty array
    let cart = JSON.parse(localStorage.getItem('courseCart') || '[]');
    
    // Check if course is already in cart
    let courseIndex = cart.indexOf(courseId)
    event = event || window.event;
    let button = event.target;

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

        fetch(`/details/${courseId}/`)  
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to load course details: ${response.status}`);
            }
            return response.text();
        })
            .then(html => {
                panelContent.innerHTML = html;
                requestAnimationFrame(() => {
                    panel.classList.add('open');
                    mainContent.classList.add('shifted');
                    courseContainer.classList.add('shifted');

                    setTimeout(() => {
                        if (clickedCard) {
                            clickedCard.scrollIntoView({ 
                                behavior: 'smooth', 
                                block: 'center'
                            });
                        }
                    }, 100);
                });
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
    
    // Get course IDs from data attributes
    const courseIds = Array.from(courseCards).map(card => card.dataset.courseId);
    
    // Get indicators from backend
    const indicators = await filterCoursesByMask(searchQuery, courseIds);

    // Update visibility based on indicators
    courseCards.forEach((card, index) => {
        if (indicators[index]) {
            card.classList.remove('hidden');
        } else {
            card.classList.add('hidden');
        }
    });
}

async function filterCoursesByMask(searchQuery, courseIds) {
    try {
        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const response = await fetch('/api/masked_filter/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify({
                search_query: searchQuery,
                course_ids: courseIds,
                similarity_threshold: 0.05
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

function updateCartDisplay() {
// 1. Get DOM elements
const cartItems = document.getElementById('cart-items');
const cartCount = document.getElementById('cart-count');
const cartCountHeader = document.getElementById('cart-count-header');

// 2. Get cart data from localStorage
const cart = JSON.parse(localStorage.getItem('courseCart') || '[]');

// 3. Clear existing content
cartItems.innerHTML = '';

if (cart.length === 0) {
    cartItems.innerHTML = '<p>Your saved schedule is empty</p>';
    cartCount.textContent = '0';
    cartCountHeader.textContent = '0';
    return;
}

// Fetch course details from server
fetch(`/cart-courses/?${cart.map(id => `ids[]=${id}`).join('&')}`)
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .catch(error => {
        console.error('Error loading cart:', error);
        cartItems.innerHTML = '<p>Error loading saved schedule</p>';
    })
    .then(data => {
        cartItems.innerHTML = '';
        data.courses.forEach(course => {
            const courseElement = document.createElement('div');
            courseElement.className = 'cart-item';
            courseElement.innerHTML = `
                <div class="cart-item-name">${course.name}</div>
                <button class="remove-from-cart" 
                        onclick="toggleCart('${course.id}')">
                        X
                </button>
            `;
            cartItems.appendChild(courseElement);
        });
        cartCount.textContent = cart.length;
        cartCountHeader.textContent = cart.length;
    });
}
