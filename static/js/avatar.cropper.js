// avatar.cropper.js

// 等待 DOM 加载完成
document.addEventListener('DOMContentLoaded', function () {
    const toggleBtn = document.getElementById('toggleBtn');
    const sidebar = document.getElementById('sidebar');
    const changeAvatarBtn = document.getElementById('change-avatar');
    const cropperModal = document.getElementById('cropper-modal');
    const imageInput = document.getElementById('imageInput');
    const dragDropArea = document.getElementById('drag-drop-area');
    const imageContainer = document.getElementById('image-container');
    const image = document.getElementById('image');
    const previewImage = document.getElementById('preview-image');
    const submitBtn = document.getElementById('submit-btn');
    const cancelBtn = document.getElementById('cancel-btn');

    let cropper = null;

    // 打开侧边栏
    toggleBtn.addEventListener('click', function () {
        sidebar.classList.toggle('active');
    });

    // 点击“更换头像”按钮时，打开裁剪模态框
    changeAvatarBtn.addEventListener('click', function () {
        cropperModal.style.display = 'flex';
    });

    // 点击取消按钮时，关闭裁剪模态框
    cancelBtn.addEventListener('click', function () {
        cropperModal.style.display = 'none';
        resetCropper();
    });

    // 点击拖拽区域时，触发文件选择
    dragDropArea.addEventListener('click', function () {
        imageInput.click();
    });

    // 处理文件上传
    imageInput.addEventListener('change', function (event) {
        const file = event.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function (e) {
                const imageURL = e.target.result;
                image.src = imageURL;
                imageContainer.style.display = 'block';

                // 等待图片加载完成后初始化裁剪工具
                image.onload = function () {
                    // 如果裁剪工具已存在，先销毁它
                    if (cropper) {
                        cropper.destroy();
                    }

                    // 使用 cropper.js 初始化裁剪器
                    cropper = new Cropper(image, {
                        aspectRatio: 1,  // 固定为1:1比例
                        viewMode: 1,  // 允许裁剪框外的区域不受限制
                        scalable: true,  // 是否可以缩放
                        zoomable: true,  // 是否可以缩放
                        cropBoxResizable: true,  // 是否允许调整裁剪框的大小
                        crop: function (event) {
                            // 这里可以获取裁剪框的位置和大小信息
                            const data = event.detail;
                            // 这里可以添加预览功能，比如实时更新预览图片
                            previewImage.style.display = 'block';
                            previewImage.src = cropper.getCroppedCanvas().toDataURL();
                        }
                    });

                    // 显示提交按钮
                    submitBtn.style.display = 'inline-block';
                };
            };
            reader.readAsDataURL(file);
        }
    });

    // 提交裁剪后的图片
    submitBtn.addEventListener('click', function () {
        const croppedImage = cropper.getCroppedCanvas().toDataURL();
        // 这里可以将裁剪后的图片上传到服务器
        uploadCroppedImage(croppedImage);

        // 关闭裁剪模态框
        cropperModal.style.display = 'none';
        resetCropper();
    });

// 处理提交按钮点击事件
submitBtn.addEventListener('click', function () {
    if (!cropper) {
        alert('裁剪器未初始化！');
        return;
    }

    const croppedImage = cropper.getCroppedCanvas().toDataURL();

    const data = {
        avatar: croppedImage
    };

    // 发送 POST 请求更新头像
    fetch('/update-avatar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('服务器响应失败');
        }
        return response.json();  // 假设服务器返回 JSON 响应
    })
    .then(result => {
        if (result.status === 'success') {
            alert('头像更新成功！');
            // 关闭裁剪模态框和重置裁剪器
            closeCropperModal();
            //刷新页面
            window.location.reload();
        } else {
            alert('头像更新失败：' + result.message);
        }
    })
    .catch(error => {
        console.error('发送请求时出错或网络响应错误：', error);
        alert('发送请求时出错，请稍后再试。');
    });
});

// 关闭裁剪模态框并重置裁剪器
function closeCropperModal() {
    cropperModal.style.display = 'none';
    resetCropper(); // 调用 resetCropper 来重置裁剪器
}

// 重置裁剪器状态
function resetCropper() {
    if (cropper) {
        cropper.destroy();  // 销毁当前裁剪器实例
        cropper = null;     // 清空裁剪器实例
    }
    image.src = '';         // 清空图片
    imageContainer.style.display = 'none';  // 隐藏图片容器
    previewImage.style.display = 'none';    // 隐藏预览图
    submitBtn.style.display = 'none';       // 隐藏提交按钮
}
})
