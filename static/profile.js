document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('toggleBtn');
    const menuItems = document.querySelectorAll('.menu li');

    // 切换侧边栏折叠/展开
    toggleBtn.addEventListener('click', function() {
        sidebar.classList.toggle('collapsed');
    });

    // 添加菜单项选中效果
    menuItems.forEach(item => {
        item.addEventListener('click', function() {
            menuItems.forEach(i => i.classList.remove('active'));
            item.classList.add('active');
        });
    });
});
