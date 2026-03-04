const API = 'https://rti58kmef9.execute-api.ap-south-1.amazonaws.com/prod';
const EMAIL_API = 'https://rti58kmef9.execute-api.ap-south-1.amazonaws.com/prod/email';

async function getPresignedUrl(params) {
    const res = await fetch(`${API}/presigned?${new URLSearchParams(params)}`);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
}

function uploadToS3(file, url, fields, onProgress) {
    const form = new FormData();
    Object.entries(fields).forEach(([k, v]) => form.append(k, v));
    form.append('file', file);
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.upload.onprogress = (e) => onProgress(e.lengthComputable ? e.loaded / e.total : 0);
        xhr.onload = () => (xhr.status >= 200 && xhr.status < 300 ? resolve() : reject(new Error(`Upload failed: ${xhr.status}`)));
        xhr.onerror = () => reject(new Error('Network error'));
        xhr.open('POST', url);
        xhr.send(form);
    });
}

async function verifyEmail(email) {
    const res = await fetch(`${EMAIL_API}?emailaddress=${encodeURIComponent(email)}`);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    return data;
}

document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('video-file');
    const fileNameSpan = document.querySelector('.file-name');
    const uploadBtn = document.getElementById('upload-btn');
    const output = document.getElementById('output');
    const wrap = document.getElementById('glass-wrap');
    const progressRing = document.getElementById('progress-ring');
    const verifyBtn = document.getElementById('verify-btn');
    const verifyEmailInput = document.getElementById('verify-email');
    const verifyOutput = document.getElementById('verify-output');
    const verifyWrap = document.getElementById('verify-wrap');

    verifyBtn.onclick = async () => {
        const email = verifyEmailInput.value.trim();
        if (!email) {
            verifyOutput.textContent = 'Please enter your email.';
            return;
        }
        verifyWrap.classList.add('verifying');
        verifyOutput.textContent = 'Sending verification...';
        try {
            await verifyEmail(email);
            verifyWrap.classList.remove('verifying');
            verifyWrap.classList.add('verified');
            verifyOutput.innerHTML = '<span class="uploaded-msg">Verification email sent! Check your inbox.</span>';
        } catch (e) {
            verifyWrap.classList.remove('verifying', 'verified');
            verifyOutput.textContent = 'Error: ' + e.message;
        }
    };

    fileInput.onchange = () => {
        const file = fileInput.files[0];
        fileNameSpan.textContent = file ? file.name : '';
        uploadBtn.disabled = !file;
    };

    uploadBtn.onclick = async () => {
        const file = fileInput.files[0];
        const email = document.getElementById('email').value.trim();
        const username = document.getElementById('username').value.trim();
        const format = document.getElementById('format').value;

        if (!file || !email || !username || !format) {
            output.textContent = 'Please fill in all fields and choose a file.';
            return;
        }

        wrap.classList.remove('uploaded');
        wrap.classList.add('uploading');
        progressRing.style.setProperty('--path-offset', '100');
        output.textContent = 'Uploading...';

        try {
            const key = `upload/${file.name}`;
            const { url, fields } = await getPresignedUrl({ key, email, username, format, status: 'PROCESSING', geturl: '' });
            await uploadToS3(file, url, fields, (pct) => progressRing.style.setProperty('--path-offset', 100 - pct * 100));

            wrap.classList.remove('uploading');
            wrap.classList.add('uploaded');
            progressRing.style.setProperty('--path-offset', '0');
            output.innerHTML = `<span class="uploaded-msg">Uploaded: ${file.name}</span><br><span class="uploaded-msg">You will receive the download link in your email.</span>`;
            fileInput.value = '';
            fileNameSpan.textContent = '';
            uploadBtn.disabled = true;
        } catch (e) {
            wrap.classList.remove('uploading', 'uploaded');
            output.textContent = 'Error: ' + e.message;
        }
    };
});
