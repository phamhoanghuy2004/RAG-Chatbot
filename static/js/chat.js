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

chooseFileBtn.addEventListener("click", function () {
    showConfirm(
        "Vui lòng đặt tên file theo định dạng:<br><strong>HDSD_&lt;Tên phần mềm&gt;_&lt;release&gt;.pdf</strong>",
        function () {
            realFileInput.click(); // Mở file picker
        }
    );
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
            if (res.status === 401){
                showConfirm(
                    "⚠ Vui lòng đăng nhập để thực hiện hành động!",
                    function () {
                        window.location.href = "/api/loginPage/";
                    }
                );
            }
            else{
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