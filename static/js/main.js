// Cyxlix Rental Management System - Core Client JS

document.addEventListener('DOMContentLoaded', () => {
    // Auto disappear notifications after 5 seconds
    setTimeout(() => {
        document.querySelectorAll('.alert, .flash-message').forEach(alert => {
            alert.style.transition = 'opacity 0.5s ease';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        });
    }, 5000);

    // 1. Live Rental Cost Estimator
    const durationInput = document.getElementById('duration');
    const pricePerHourInput = document.getElementById('price_per_hour');
    const costEstimateSpan = document.getElementById('cost_estimate');
    const savingsEstimateSpan = document.getElementById('savings_estimate');

    if (durationInput && pricePerHourInput && costEstimateSpan) {
        const calculateCost = () => {
            const duration = parseFloat(durationInput.value) || 0;
            const price = parseFloat(pricePerHourInput.value) || 0;
            const total = duration * price;
            costEstimateSpan.textContent = `₹${total.toFixed(2)}`;

            // Standard savings vs car (fuel/maint. savings ≈ ₹4.50 per km; assume avg speed 15km/h = 15km per hour)
            if (savingsEstimateSpan) {
                const estimatedDistance = duration * 15; 
                const savings = estimatedDistance * 4.50;
                savingsEstimateSpan.textContent = `₹${savings.toFixed(2)}`;
            }
        };
        durationInput.addEventListener('input', calculateCost);
        calculateCost();
    }

    // 2. Chatbot Functionality
    const chatForm = document.getElementById('chat-form');
    const chatInput = document.getElementById('chat-input');
    const chatMessages = document.getElementById('chat-messages');

    if (chatForm && chatInput && chatMessages) {
        const appendMessage = (sender, text) => {
            const bubble = document.createElement('div');
            bubble.classList.add('message-bubble');
            bubble.classList.add(sender === 'user' ? 'user-msg' : 'bot-msg');
            bubble.innerHTML = text.replace(/\n/g, '<br>');
            chatMessages.appendChild(bubble);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        };

        const sendMessage = async (messageText) => {
            if (!messageText.trim()) return;

            appendMessage('user', messageText);
            chatInput.value = '';

            // Show typing indicator
            const typingBubble = document.createElement('div');
            typingBubble.classList.add('message-bubble', 'bot-msg');
            typingBubble.id = 'typing-indicator';
            typingBubble.textContent = 'Typing...';
            chatMessages.appendChild(typingBubble);
            chatMessages.scrollTop = chatMessages.scrollHeight;

            try {
                const response = await fetch('/chatbot/send', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: messageText })
                });

                const data = await response.json();
                
                // Remove typing indicator
                const indicator = document.getElementById('typing-indicator');
                if (indicator) indicator.remove();

                appendMessage('bot', data.response);
            } catch (error) {
                console.error('Error sending message:', error);
                const indicator = document.getElementById('typing-indicator');
                if (indicator) indicator.remove();
                appendMessage('bot', "Sorry, I'm having trouble connecting right now. Please try again.");
            }
        };

        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            sendMessage(chatInput.value);
        });

        // Chat Chip Interactions
        document.querySelectorAll('.chat-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                sendMessage(chip.textContent);
            });
        });
    }

    // 3. Companion Mode Live Stopwatch & Simulator
    const startRideBtn = document.getElementById('start-ride-btn');
    const endRideBtn = document.getElementById('end-ride-btn');
    const stopWatchText = document.getElementById('live-stopwatch');
    const pulseRing = document.querySelector('.pulse-ring');
    
    // Companion display values
    const liveSpeedText = document.getElementById('live-speed');
    const liveDistanceText = document.getElementById('live-distance');
    const liveCarbonText = document.getElementById('live-carbon');
    const liveSavingsText = document.getElementById('live-savings');

    // Input fields for ending a ride
    const companionForm = document.getElementById('companion-form');
    const finalSecondsInput = document.getElementById('final-seconds');
    const finalDistanceInput = document.getElementById('final-distance');

    if (startRideBtn && endRideBtn) {
        let timerInterval = null;
        let elapsedSeconds = 0;

        // Load active ride if already running in session storage
        if (sessionStorage.getItem('rideActive') === 'true') {
            const startTimeStamp = parseInt(sessionStorage.getItem('rideStartTime')) || Date.now();
            elapsedSeconds = Math.floor((Date.now() - startTimeStamp) / 1000);
            startRideSimulation();
        }

        function formatTime(totalSeconds) {
            const hrs = Math.floor(totalSeconds / 3600).toString().padStart(2, '0');
            const mins = Math.floor((totalSeconds % 3600) / 60).toString().padStart(2, '0');
            const secs = (totalSeconds % 60).toString().padStart(2, '0');
            return `${hrs}:${mins}:${secs}`;
        }

        function startRideSimulation() {
            sessionStorage.setItem('rideActive', 'true');
            if (!sessionStorage.getItem('rideStartTime')) {
                sessionStorage.setItem('rideStartTime', Date.now().toString());
            }

            startRideBtn.classList.add('d-none');
            endRideBtn.classList.remove('d-none');
            if (pulseRing) pulseRing.classList.add('active');

            timerInterval = setInterval(() => {
                const startTimeStamp = parseInt(sessionStorage.getItem('rideStartTime')) || Date.now();
                elapsedSeconds = Math.floor((Date.now() - startTimeStamp) / 1000);
                
                if (stopWatchText) stopWatchText.textContent = formatTime(elapsedSeconds);

                // Simulate progress
                // Average cycling speed = 16 km/h => 0.0044 km/sec
                const speed = 15.5 + Math.sin(elapsedSeconds / 10) * 2; // slight fluctuations
                const distance = elapsedSeconds * 0.0044; // 16 km/h approx
                const carbon = distance * 0.12; // 0.12 kg/km
                const savings = distance * 4.50; // ₹4.50/km

                if (liveSpeedText) liveSpeedText.textContent = `${speed.toFixed(1)} km/h`;
                if (liveDistanceText) liveDistanceText.textContent = `${distance.toFixed(2)} km`;
                if (liveCarbonText) liveCarbonText.textContent = `${carbon.toFixed(2)} kg`;
                if (liveSavingsText) liveSavingsText.textContent = `₹${savings.toFixed(2)}`;

            }, 1000);
        }

        startRideBtn.addEventListener('click', () => {
            elapsedSeconds = 0;
            sessionStorage.setItem('rideStartTime', Date.now().toString());
            startRideSimulation();
        });

        endRideBtn.addEventListener('click', () => {
            clearInterval(timerInterval);
            sessionStorage.removeItem('rideActive');
            sessionStorage.removeItem('rideStartTime');

            const finalDistance = elapsedSeconds * 0.0044; // match calculations

            if (finalSecondsInput) finalSecondsInput.value = elapsedSeconds;
            if (finalDistanceInput) finalDistanceInput.value = finalDistance.toFixed(2);

            if (companionForm) {
                companionForm.submit();
            }
        });
    }

    // SOS Trigger Demo
    const sosBtn = document.getElementById('sos-btn');
    if (sosBtn) {
        sosBtn.addEventListener('click', () => {
            alert('🚨 EMERGENCY PROTOCOL TRIGGERED: An alert with your GPS coordinates is being dispatched to system operators and emergency authorities. Please stay in a safe area.');
        });
    }
});
