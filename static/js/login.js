const form = document.getElementById('loginForm');
const errorMsg = document.getElementById('errorMsg');

form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorMsg.style.display = 'none';

    const data = {
        username: form.username.value,
        password: form.password.value
    };

    try {
        const res = await fetch('/rag/api/login/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (res.ok) {
            window.location.href = '/';
        } else {
            const error = await res.json();
            errorMsg.innerText = error.error || "Có lỗi xảy ra!";
            errorMsg.style.display = 'block';
        }
    } catch (err) {
        errorMsg.innerText = "Không thể kết nối đến server!";
        errorMsg.style.display = 'block';
    }
});