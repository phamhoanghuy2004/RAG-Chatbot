function toggleActive(id, isActive) {
    alert("Toggle prompt " + id + " | Trạng thái hiện tại: " + isActive);
}

function deletePrompt(id) {
    alert("Xóa prompt " + id);
}

function editPrompt(button) {
    // lấy data từ button
    const id = button.getAttribute("data-id");
    const type = button.getAttribute("data-type");
    const content = button.getAttribute("data-content");
    const description = button.getAttribute("data-description");
    const isActive = button.getAttribute("data-active") === "True"; // Django render True/False

    // đổ vào form
    document.getElementById("form-title").innerText = "Sửa Prompt";
    document.getElementById("prompt-id").value = id;
    document.getElementById("type").value = type;
    document.getElementById("content").value = content;
    document.getElementById("description").value = description;
    document.getElementById("is_active").checked = isActive;
}

async function savePrompt(e) {
    e.preventDefault();
    // TODO: code gửi AJAX hoặc submit form
    const id = document.getElementById("prompt-id").value;
    const type = document.getElementById("type").value;
    const content = document.getElementById("content").value;
    const description = document.getElementById("description").value;
    const is_active = document.getElementById("is_active").checked;

    try {
        const res = await fetch("/rag/api/addprompt/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            credentials: "include", // gửi kèm cookie access_token
            body: JSON.stringify({
                id: id || null,
                type: type,
                content: content,
                description: description,
                is_active: is_active,
            }),
        });

        if (res.ok) {
            const data = await res.json();
            showAlert("✅ Thành công", data.message || "Đã lưu Prompt!");
            resetForm();
            window.location.reload();
        } else {
            const error = await res.json();
            if (res.status === 401) {
                showConfirm(
                    "⚠ Vui lòng đăng nhập để thực hiện hành động!",
                    function () {
                        window.location.href = "/rag/api/loginPage/";
                    }
                );
            } else {
                showAlert(
                    "❌ Thất bại",
                    `Lưu Prompt thất bại.<br>Lỗi: ${error.error || "Không rõ nguyên nhân."}`
                );
            }
        }
    } catch (err) {
        showAlert("❌ Lỗi hệ thống", err.message);
    }
}

function resetForm() {
    document.getElementById("form-title").textContent = "Thêm Prompt";
    document.getElementById("prompt-form").reset();
    document.getElementById("prompt-id").value = "";
}

// gắn event submit form
document.getElementById("prompt-form").addEventListener("submit", savePrompt);



function showAlert(title, message) {
    const alertBox = document.getElementById("customAlert");
    document.getElementById("alertTitle").innerHTML = title;
    document.getElementById("alertMessage").innerHTML = message;
    alertBox.style.display = "flex";

    document.getElementById("alertOk").onclick = function () {
        alertBox.style.display = "none";
    };
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