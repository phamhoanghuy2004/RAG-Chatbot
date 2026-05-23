const chatBox = document.getElementById('chat-box');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const uploadForm = document.getElementById('upload-form');
const chooseFileBtn = document.getElementById("chooseFileBtn");
const realFileInput = document.getElementById("realFileInput");
const fileNameSpan = document.getElementById('file-name');
const loadingSpinner = document.getElementById('loading-spinner');
const docSelect = document.getElementById('doc-select');
const modelSelect = document.getElementById('model-select')
const chatGreeting = document.getElementById('chat-greeting');
const loadingDots = document.getElementById('loading-dots');

// // Hybrid retrieval elements
// const hybridCheckbox = document.getElementById('hybrid-checkbox');
// const weightControls = document.getElementById('weight-controls');
// const denseWeight = document.getElementById('dense-weight');
// const denseValue = document.getElementById('dense-value');

// // Handle hybrid toggle
// if (hybridCheckbox && weightControls) {
//     hybridCheckbox.addEventListener('change', function() {
//         if (this.checked) {
//             weightControls.style.display = 'flex';
//         } else {
//             weightControls.style.display = 'none';
//         }
//     });
// }

// // Handle weight slider
// if (denseWeight && denseValue) {
//     denseWeight.addEventListener('input', function() {
//         const dense = parseFloat(this.value);
//         const sparse = (1.0 - dense).toFixed(1);
//         denseValue.textContent = `${dense}:${sparse}`;
//     });
// }

chooseFileBtn.addEventListener("click", function () {
    realFileInput.click(); // Mở file picker
});

realFileInput.addEventListener("change", function () {
    fileNameSpan.textContent = this.files.length > 0 ? this.files[0].name : "";
});

uploadForm.onsubmit = async function (e) {
    e.preventDefault();
    if (!realFileInput.files || realFileInput.files.length === 0) {
        showAlert("⚠ Lỗi", "Vui lòng chọn file PDF!");
        return;
    }
    loadingSpinner.style.display = 'flex';
    const formData = new FormData(uploadForm);
    try {
        const res = await fetch('/api/upload/', {
            method: 'POST',
            body: formData
        });
        if (res.ok) {
            showAlert("✅ Thành công", "Tải PDF thành công!");
            fileNameSpan.textContent = '';
            realFileInput.value = '';
            location.reload(); // ✅ Reload trang
        } else {
            const error = await res.json();
            if (res.status === 401) {
                showConfirm(
                    "⚠ Vui lòng đăng nhập để thực hiện hành động!",
                    function () {
                        window.location.href = "/api/loginPage/";
                    }
                );
            } else {
                showAlert("❌ Thất bại", `Tải PDF thất bại.<br>Lỗi: ${error.error || "Không rõ nguyên nhân."}`);
            }
        }
    } catch (err) {
        showAlert("❌ Lỗi kết nối", "Không thể kết nối máy chủ.");
    } finally {
        loadingSpinner.style.display = 'none';
    }
};

chatForm.onsubmit = async function (e) {
    e.preventDefault();

    const question = userInput.value.trim();
    if (!question) return;

    // Ẩn lời chào nếu đang hiển thị
    if (chatGreeting && chatGreeting.style.display !== 'none') {
        chatGreeting.style.display = 'none';
    }

    const selectedSource = docSelect.value;
    const selectedModel = modelSelect.value;

    // Hiển thị câu hỏi của người dùng
    const userBubble = document.createElement('div');
    userBubble.className = 'chatgpt-bubble user';
    userBubble.innerHTML = `<div class="bubble">${question}</div>`;
    chatBox.appendChild(userBubble);

    userInput.value = '';
    chatBox.scrollTop = chatBox.scrollHeight;

    // Hiển thị loading dots
    loadingDots.style.display = 'flex';
    chatBox.appendChild(loadingDots);
    chatBox.scrollTop = chatBox.scrollHeight;

    // Cho browser cơ hội render loading
    await new Promise(requestAnimationFrame);

    if (selectedModel.startsWith("compare:")) {
        const [model1, model2] = selectedModel.replace("compare:", "").split("VS");

        try {
            const res = await fetch('/api/chat/compare/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    question,
                    source: selectedSource,
                    model1,
                    model2
                })
            });

            const reader = res.body.getReader();
            const decoder = new TextDecoder("utf-8");

            // Tạo container và hai khung bubble
            const compareContainer = document.createElement('div');
            compareContainer.className = "compare-bubbles";

            const bubble1 = document.createElement('div');
            bubble1.className = "compare-bubble model1 markdown-body";

            const bubble2 = document.createElement('div');
            bubble2.className = "compare-bubble model2 markdown-body";

            compareContainer.appendChild(bubble1);
            compareContainer.appendChild(bubble2);
            chatBox.appendChild(compareContainer);
            chatBox.scrollTop = chatBox.scrollHeight;

            let receivedCount = 0;
            let buffer = '';
            while (true) {
                const {
                    done,
                    value
                } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, {
                    stream: true
                });

                const regex = /###BEGIN_model(1|2)###\n([\s\S]*?)\n###END_model\1###/g;
                let match;
                while ((match = regex.exec(buffer)) !== null) {
                    const modelIndex = match[1];
                    const content = match[2].trim();
                    const html = marked.parse(content || "Không có phản hồi.");
                    const targetBubble = modelIndex === "1" ? bubble1 : bubble2;

                    typeWriterEffect(targetBubble, html, 1);
                    receivedCount++;
                }

                buffer = buffer.replace(regex, '');

                if (receivedCount >= 2) break;
            }

        } catch (err) {
            const errorBubble = document.createElement('div');
            errorBubble.className = 'chatgpt-bubble bot';
            errorBubble.innerHTML = `<div class='bubble'>❌ Lỗi phản hồi từ máy chủ.</div>`;
            chatBox.appendChild(errorBubble);
        } finally {
            loadingDots.style.display = 'none';
        }
    } else {
        try {
            // // Get hybrid retrieval settings
            // const useHybrid = hybridCheckbox ? hybridCheckbox.checked : false;
            // const denseWeightValue = denseWeight ? parseFloat(denseWeight.value) : 0.7;
            // const sparseWeightValue = 1.0 - denseWeightValue;
            
            // const requestData = {
            //     question,
            //     source: selectedSource,
            //     model: selectedModel
            // };
            
            // // Add hybrid settings if enabled
            // if (useHybrid) {
            //     requestData.use_hybrid = true;
            //     requestData.hybrid_weights = [denseWeightValue, sparseWeightValue];
            // }
            
            const res = await fetch('/api/chat/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    question,
                    source: selectedSource,
                    model: selectedModel
                })
            });

            const data = await res.json();

            const htmlAnswer = marked.parse(data.answer || "Không có phản hồi.");

            const botBubble = document.createElement('div');
            botBubble.className = "chatgpt-bubble bot";

            const bubbleContent = document.createElement('div');
            bubbleContent.className = "bubble markdown-body";
            botBubble.appendChild(bubbleContent);

            chatBox.appendChild(botBubble);
            chatBox.scrollTop = chatBox.scrollHeight;

            typeWriterEffect(bubbleContent, htmlAnswer, 1);

            // Append feedback form
            // Thêm form đánh giá ngay dưới câu trả lời
            const feedbackForm = appendFeedbackForm(data.log_id);
            chatBox.appendChild(feedbackForm);

        } catch (err) {
            const errorBubble = document.createElement('div');
            errorBubble.className = 'chatgpt-bubble bot';
            errorBubble.innerHTML = `<div class='bubble'>❌ Lỗi phản hồi từ máy chủ.</div>`;
            chatBox.appendChild(errorBubble);
        } finally {
            loadingDots.style.display = 'none';
        }
    }
};


function typeWriterEffect(targetElement, html, speed = 1) {
    let i = 0;

    function type() {
        if (i <= html.length) {
            targetElement.innerHTML = html.slice(0, i);
            // Tự động cuộn xuống cuối mỗi lần thêm ký tự
            targetElement.parentElement.parentElement.scrollTop = targetElement.parentElement.parentElement.scrollHeight;
            i++;
            setTimeout(type, speed);
        }
    }
    type();
}

function showConfirm(message, onYes) {
    const confirmBox = document.getElementById("customConfirm");
    confirmBox.querySelector("p").innerHTML = message;
    confirmBox.style.display = "flex";

    document.getElementById("confirmYes").onclick = function () {
        confirmBox.style.display = "none";
        onYes();
    };
    document.getElementById("confirmNo").onclick = function () {
        confirmBox.style.display = "none";
    };
}

function showAlert(title, message) {
    const alertBox = document.getElementById("customAlert");
    document.getElementById("alertTitle").innerHTML = title;
    document.getElementById("alertMessage").innerHTML = message;
    alertBox.style.display = "flex";

    document.getElementById("alertOk").onclick = function () {
        alertBox.style.display = "none";
    };
}

// Restore selection on load
if (sessionStorage.getItem('selectedDoc')) {
    docSelect.value = sessionStorage.getItem('selectedDoc');
}

// Save changes once user pick a document
docSelect.addEventListener('change', () => {
    sessionStorage.setItem('selectedDoc', docSelect.value);
    sessionStorage.setItem('docSelected', docSelect.value ? '1' : '');
});

// Pop up message if no doc selected yet - appear only once in every tab
(function () {
    function showDocReminderIfNeeded() {
        if (sessionStorage.getItem("docSelected") === "1") return;
        const select = document.getElementById("doc-select");
        if (!select) return;

        const hasSelection = select.value && select.value.trim() !== "";
        if (!hasSelection) {
            showAlert("Thông báo", "Vui lòng chọn tài liệu phần mềm ở bên trên nhé.");
        }
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", showDocReminderIfNeeded);
    } else {
        setTimeout(showDocReminderIfNeeded, 0);
    }
})();

function appendFeedbackForm(logId) {
    const feedbackDiv = document.createElement('div');
    feedbackDiv.className = 'feedback-form';
    feedbackDiv.dataset.logId = logId;

    // Accuracy label
    const accuracyLabel = document.createElement('label');
    accuracyLabel.textContent = 'Độ chính xác (%):';
    feedbackDiv.appendChild(accuracyLabel);

    // Accuracy input
    const accuracyInput = document.createElement('input');
    accuracyInput.type = 'number';
    accuracyInput.className = 'accuracy-input';
    accuracyInput.min = 0;
    accuracyInput.max = 100;
    accuracyInput.step = 1;
    accuracyInput.style.width = '60px';
    feedbackDiv.appendChild(accuracyInput);

    // Satisfaction label
    const satisfactionLabel = document.createElement('span');
    satisfactionLabel.style.marginLeft = '20px';
    satisfactionLabel.textContent = 'Mức độ hài lòng:';
    feedbackDiv.appendChild(satisfactionLabel);

    // Stars
    const starsSpan = document.createElement('span');
    starsSpan.className = 'stars';
    let selectedStar = 0;
    for (let i = 1; i <= 5; i++) {
        const star = document.createElement('span');
        star.className = 'star';
        star.dataset.value = i;
        star.innerHTML = '&#9733;'; // Unicode star character
        star.onclick = function () {
            selectedStar = parseInt(this.dataset.value);
            starsSpan.querySelectorAll('.star').forEach((s, idx) => {
                if (idx < selectedStar) s.classList.add('selected');
                else s.classList.remove('selected');
            });
        };
        starsSpan.appendChild(star);
    }
    feedbackDiv.appendChild(starsSpan);

    // Submit button
    const submitBtn = document.createElement('button');
    submitBtn.className = 'submit-feedback-btn';
    submitBtn.textContent = 'Gửi đánh giá';
    submitBtn.onclick = async function () {
        const accuracy = accuracyInput.value;
        if (!accuracy) {
            alert("Vui lòng nhập độ chính xác!");
            return;
        }
        if (!selectedStar) {
            alert("Vui lòng chọn mức độ hài lòng!");
            return;
        }
        try {
            const res = await fetch('/api/feedback/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include', // để gửi cookie access_token
                body: JSON.stringify({
                    log_id: logId,
                    accuracy: accuracy,
                    user_satisfaction: selectedStar
                })
            });

            if (res.ok) {
                const data = await res.json();
                showAlert("✅ Thành công", data.message || "Đã gửi feedback!");
                submitBtn.textContent = "Đánh giá lại";
            } else {
                const error = await res.json();
                if (res.status === 401) {
                    showConfirm(
                        "⚠ Vui lòng đăng nhập để thực hiện hành động!",
                        function () {
                            window.location.href = "/api/loginPage/";
                        }
                    );
                } else {
                    showAlert("❌ Thất bại", `Gửi feedback thất bại.<br>Lỗi: ${error.error || "Không rõ nguyên nhân."}`);
                }
            }
        } catch (e) {
            showAlert("❌ Lỗi hệ thống", e.message);
        }
    };
    feedbackDiv.appendChild(submitBtn);

    return feedbackDiv;
}