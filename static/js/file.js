
        // 页面加载完成后执行的初始化逻辑
        document.addEventListener('DOMContentLoaded', initPage);

        // 初始化页面的主函数，整合各功能模块的初始化操作
        function initPage() {
            const pageElements = getPageElements();
            setupModalBox(pageElements);
            setupFileUpload(pageElements);
            setupSidebar(pageElements);
            setupMenuItemClick(pageElements);
            listFiles();
            setupShareButtons();
        }

        // 获取页面相关元素的函数
        function getPageElements() {
            return {
                openModalBtn: document.getElementById('openModalBtn'),
                uploadModal: document.getElementById('uploadModal'),
                closeBtn: document.getElementById('uploadModal').querySelector('.close'),
                uploadForm: document.getElementById('upload-form'),
                uploadProgress: document.getElementById('upload-progress'),
                progressPercentage: document.getElementById('progress-percentage'),
                uploadRate: document.getElementById('upload-rate'),
                fileList: document.getElementById('file-list'),
                errorMessageContainer: document.getElementById('error-message-container'),
                sidebar: document.getElementById('sidebar'),
                toggleBtn: document.getElementById('toggleBtn'),
                menuItems: document.querySelectorAll('.menu li'),
                shareButtons: document.querySelectorAll('.share-btn')
            };
        }

        // 设置模态框相关事件（打开、关闭等）
        function setupModalBox({ openModalBtn, uploadModal, closeBtn }) {
            openModalBtn.addEventListener('click', () => {
                uploadModal.style.display = "block";
            });

            closeBtn.addEventListener('click', () => {
                uploadModal.style.display = "none";
            });

            window.addEventListener('click', (event) => {
                if (event.target === uploadModal) {
                    uploadModal.style.display = "none";
                }
            });
        }

        // 设置文件上传相关逻辑
        function setupFileUpload({ uploadForm, uploadProgress, progressPercentage, uploadRate, fileList, errorMessageContainer }) {
            uploadForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const fileInput = document.getElementById('file-input');
                const file = fileInput.files[0];
                if (!file) {
                    showErrorMessage('请选择要上传的文件');
                    return;
                }

                const formData = new FormData();
                formData.append('file', file);

                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/file/upload', true);
                xhr.setRequestHeader('Authorization', `Bearer ${localStorage.getItem('loggedInUsername')}`);
                setupUploadProgress(xhr, uploadProgress, progressPercentage, uploadRate);
                xhr.onload = () => handleUploadResponse(xhr, fileList, errorMessageContainer);
                xhr.send(formData);
            });
        }

        // 设置文件上传进度相关逻辑
        function setupUploadProgress(xhr, uploadProgress, progressPercentage, uploadRate) {
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percentComplete = Math.round((e.loaded / e.total) * 100);
                    uploadProgress.value = percentComplete;
                    progressPercentage.textContent = percentComplete + '%';
                }
            }, false);

            let startTime;
            xhr.addEventListener('loadstart', () => {
                startTime = Date.now();
            });
            xhr.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const currentTime = Date.now();
                    const elapsedTime = (currentTime - startTime) / 1000;
                    const uploadedBytes = e.loaded;
                    const uploadSpeed = Math.round(uploadedBytes / elapsedTime / 1024);
                    uploadRate.textContent = `上传速率: ${uploadSpeed} KB/s`;
                }
            });
        }

        // 处理文件上传后的响应
        function handleUploadResponse(xhr, fileList, errorMessageContainer) {
            if (xhr.status === 200) {
                const data = JSON.parse(xhr.responseText);
                if (data.error) {
                    showErrorMessage(data.error);
                } else {
                    listFiles();
                }
            } else if (xhr.status === 400) {
                const data = JSON.parse(xhr.responseText);
                showErrorMessage(data.error);
            } else {
                console.error('文件上传出错：', xhr.statusText);
                showErrorMessage('文件上传失败，请稍后重试');
            }
            // 上传完成后隐藏模态框（可根据实际需求调整此处逻辑）
            const uploadModal = document.getElementById('uploadModal');
            uploadModal.style.display = "none";
        }

        // 设置侧边栏切换逻辑
        function setupSidebar({ toggleBtn, sidebar }) {
            toggleBtn.addEventListener('click', () => {
                sidebar.classList.toggle('collapsed');
            });
        }

        // 设置菜单项点击逻辑
        function setupMenuItemClick({ menuItems }) {
            menuItems.forEach((item) => {
                item.addEventListener('click', () => {
                    menuItems.forEach((i) => i.classList.remove('active'));
                    item.classList.add('active');
                });
            });
        }

        // 获取文件列表并展示
        function listFiles() {
            const fileList = document.getElementById('file-list');
            const errorMessageContainer = document.getElementById('error-message-container');
            fetch('/api/file_list')
             .then(response => {
                    if (!response.ok) {
                        throw new Error('获取文件列表失败，状态码：' + response.status);
                    }
                    return response.json();
                })
             .then(data => {
                    if (data.error) {
                        showErrorMessage(data.error);
                    } else {
                        fileList.innerHTML = '';
                        data.forEach((file) => appendFileListItem(file, fileList));
                    }
                })
             .catch(error => {
                    console.error('获取文件列表出错：', error);
                    showErrorMessage('没有获取到用户记录');
                });
        }

        // 向文件列表中添加单个文件的展示项
        function appendFileListItem(file, fileList) {
            const listItem = document.createElement('li');
            const fileName = document.createElement('b');
            fileName.textContent = file.file_name;
            const fileSize = document.createElement('span');
            // fileSize.textContent = `大小: ${file.file_size} 字节`;
            const fileType = document.createElement('span');
            // fileType.textContent = `类型: ${file.file_type}`;
            const createdTime = document.createElement('span');
            createdTime.textContent = `上传时间: ${file.created_at}`;
            const modifiedTime = document.createElement('span');
            // modifiedTime.textContent = `修改时间: ${file.modified_at}`;
            const md5 = document.createElement('span');
            md5.textContent = `md5: ${file.md5}`;
            const downloadLink = document.createElement('a');
            downloadLink.href = `/api/file_download?file_id=${file.file_id}`;
            downloadLink.textContent = '下载';
            const shareButton = document.createElement('button');
            shareButton.textContent = '分享';
            shareButton.dataset.fileId = file.file_id;

            shareButton.addEventListener('click', handleShareButtonClick);

            listItem.appendChild(fileName);
            listItem.appendChild(fileSize);
            listItem.appendChild(fileType);
            listItem.appendChild(createdTime);
            listItem.appendChild(modifiedTime);
            listItem.appendChild(md5);
            listItem.appendChild(downloadLink);
            listItem.appendChild(shareButton);
            fileList.appendChild(listItem);
        }

        function handleShareButtonClick() {
            // 记录函数开始执行，方便查看整体流程顺序
            console.log('handleShareButtonClick 函数开始执行');
        
            const fileId = this.dataset.fileId;
            console.log('分享按钮点击，获取到的原始fileId：', fileId);
            // 输出fileId的类型，进一步确认其数据类型是否符合预期
            console.log('获取到的原始fileId的类型：', typeof fileId);
            // 输出fileId的长度，查看是否存在意外的额外字符等情况
            console.log('获取到的原始fileId的长度：', fileId.length);
        
            if (!fileId) {
                console.log('fileId为空，无法获取文件 id，提示用户刷新页面后重试');
                showErrorMessage('无法获取文件 id，请刷新页面后重试');
                return;
            }
        
            const fileIdNumber = parseInt(fileId, 10);
            console.log('将fileId转换为数字类型，转换后的fileIdNumber：', fileIdNumber);
            console.log('转换后的fileIdNumber是否为NaN：', isNaN(fileIdNumber));
            if (isNaN(fileIdNumber)) {
                console.error('文件id转换为数字失败，原始fileId：', fileId);
                console.log('提示用户文件id格式不正确，让用户刷新页面后重试');
                showErrorMessage('文件id格式不正确，请刷新页面后重试');
                return;
            }
        
            console.log('即将发送给后端的文件ID（数字类型）：', fileIdNumber);
            // 记录fetch请求即将发送，方便在网络请求相关问题时排查顺序
            console.log('即将发送文件分享请求，请求URL：/api/file_share');
        
            fetch('/api/file_share', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    file_id: fileIdNumber
                })
            })
          .then(response => {
                    console.log('文件分享请求已发送，收到服务器响应');
                    console.log('响应状态码：', response.status);
                    console.log('响应状态文本：', response.statusText);
                    if (!response.ok) {
                        console.error('文件分享请求失败，状态码：', response.status);
                        console.log('抛出文件分享请求失败的错误信息');
                        throw new Error('文件分享请求失败，状态码：' + response.status);
                    }
                    console.log('响应正常，准备解析响应数据为JSON格式');
                    return response.json();
                })
          .then(data => {
                    console.log('已成功将响应数据解析为JSON格式，数据内容：', data);
                    if (data.success) {
                        const downloadUrl = data.data[0];
                        const code = data.data[1];
                        console.log('文件共享成功，准备展示成功提示信息');
                        showSuccessMessage(`文件共享成功！下载地址：${downloadUrl}，验证码：${code}`);
                    } else {
                        console.error('文件分享失败，后端返回错误信息：', data.error);
                        console.log('准备展示后端返回的错误信息给用户');
                        showErrorMessage(data.error);
                    }
                })
          .catch(error => {
                    console.error('文件分享出错：', error);
                    console.log('开始处理文件分享请求的catch块中的错误情况');
                    let errorMessage = '未知错误，请稍后重试';
                    if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
                        errorMessage = '网络连接出现问题，请检查网络后重试';
                    }
                    console.error('最终确定的展示给用户的错误信息：', errorMessage);
                    console.log('准备展示错误信息给用户');
                    showErrorMessage(errorMessage);
                    const errorLogData = {
                        type: '文件分享错误',
                        message: errorMessage,
                        timestamp: new Date().getTime()
                    };
                    console.log('准备将错误日志数据发送到服务器（此处需根据实际的sendErrorLogToServer函数实现确认是否成功发送）');
                    sendErrorLogToServer(errorLogData);
                });
            console.log('handleShareButtonClick 函数执行结束（注意，这里只是函数主体逻辑结束，异步操作还在继续）');
        }

        // 为所有分享按钮添加点击事件监听器，复用handleShareButtonClick函数
        function setupShareButtons() {
            const shareButtons = document.querySelectorAll('.share-btn');
            shareButtons.forEach((button) => {
                button.addEventListener('click', handleShareButtonClick);
            });
        }

        // 用于显示错误提示信息的函数
        function showErrorMessage(message) {
            const errorMessageDiv = document.createElement('div');
            errorMessageDiv.classList.add('error-message');
            errorMessageDiv.textContent = message;
            const errorMessageContainer = document.getElementById('error-message-container');
            errorMessageContainer.appendChild(errorMessageDiv);
            setTimeout(() => {
                errorMessageDiv.remove();
            }, 5000);
        }

        // 用于显示成功提示信息的函数
        function showSuccessMessage(message) {
            const successMessageDiv = document.createElement('div');
            successMessageDiv.classList.add('success-message');
            successMessageDiv.textContent = message;
            const errorMessageContainer = document.getElementById('error-message-container');
            errorMessageContainer.appendChild(successMessageDiv);
            setTimeout(() => {
                successMessageDiv.remove();
            }, 3000);
        }

        // 这里假设的向服务器发送错误日志的函数，实际需根据后端接口实现
        function sendErrorLogToServer(errorLogData) {
            // 发送请求到服务器记录错误日志的逻辑，此处省略具体实现
        }
