$(document).ready(function () {
    // 头像菜单显示隐藏逻辑
    $('.user-avatar-container,.guest-avatar-container').hover(
        function () {
            $(this).find('.user-avatar-menu,.guest-avatar-menu').stop(true, true).slideDown(200);
        },
        function () {
            $(this).find('.user-avatar-menu,.guest-avatar-menu').stop(true, true).slideUp(200);
        }
    );

    // 点击菜单外部时隐藏菜单
    $(document).mouseup(function (e) {
        var containers = $(".user-avatar-container,.guest-avatar-container");
        if (!containers.is(e.target) && containers.has(e.target).length === 0) {
            containers.find(".user-avatar-menu,.guest-avatar-menu").slideUp(200);
        }
    });

    // 导航栏搜索图标点击事件（可后续扩展实现搜索功能）
    $('.navbar-icons.fa-search').click(function () {
        alert('搜索功能正在开发中，敬请期待！');
    });

    // 导航栏消息图标点击事件（可后续扩展实现消息提醒功能）
    $('.navbar-icons.fa-bell').click(function () {
        alert('消息提醒功能正在开发中，敬请期待！');
    });

    // 导航栏用户图标点击事件（可后续扩展实现用户相关功能）
    $('.navbar-icons.fa-user').click(function () {
        if ($('.user-avatar-container').length > 0) {
            $('.user-avatar-container').find('.user-avatar-menu').slideDown(200);
        } else if ($('.guest-avatar-container').length > 0) {
            $('.guest-avatar-container').find('.guest-avatar-menu').slideDown(200);
        }
    });

    // 快捷登录按钮点击事件（模拟，可替换为实际逻辑）
    $('.guest-avatar-menu.quick-login-button').click(function () {
        // 这里可以添加实际的快捷登录逻辑，比如调用接口等，目前先模拟弹出提示
        alert('快捷登录功能正在开发中，暂时为你模拟登录成功，即将跳转到首页。');
        // 模拟登录成功后跳转到首页（这里只是简单的页面跳转模拟，实际需要根据路由机制调整）
        window.location.href = "/";
    });

    // 卡片链接点击效果（添加简单的点击反馈，可根据实际需求扩展）
    $('.card-link').click(function () {
        $(this).addClass('active');
        setTimeout(() => {
            $(this).removeClass('active');
        }, 300);
    });
});
$(document).ready(function () {
    // 头像菜单显示隐藏逻辑
    $('.user - avatar - container,.guest - avatar - container').hover(
        function () {
            $(this).find('.user - avatar - menu,.guest - avatar - menu').stop(true, true).slideDown(200);
        },
        function () {
            $(this).find('.user - avatar - menu,.guest - avatar - menu').stop(true, true).slideUp(200);
        }
    );

    // 点击菜单外部时隐藏菜单
    $(document).mouseup(function (e) {
        var containers = $(".user - avatar - container,.guest - avatar - container");
        if (!containers.is(e.target) && containers.has(e.target).length === 0) {
            containers.find(".user - avatar - menu,.guest - avatar - menu").slideUp(200);
        }
    });

    // 导航栏搜索图标点击事件（可后续扩展实现搜索功能）
    $('.navbar - icons.fa - search').click(function () {
        alert('搜索功能正在开发中，敬请期待！');
    });

    // 导航栏消息图标点击事件（可后续扩展实现消息提醒功能）
    $('.navbar - icons.fa - bell').click(function () {
        alert('消息提醒功能正在开发中，敬请期待！');
    });

    // 导航栏用户图标点击事件（可后续扩展实现用户相关功能）
    $('.navbar - icons.fa - user').click(function () {
        if ($('.user - avatar - container').length > 0) {
            $('.user - avatar - container').find('.user - avatar - menu').slideDown(200);
        } else if ($('.guest - avatar - container').length > 0) {
            $('.guest - avatar - container').find('.guest - avatar - menu').slideDown(200);
        }
    });

    // 快捷登录按钮点击事件（模拟，可替换为实际逻辑）
    $('.guest - avatar - menu.quick - login - button').click(function () {
        alert('快捷登录功能正在开发中，暂时为你模拟登录成功，即将跳转到首页。');
        window.location.href = "/";
    });

    // 卡片链接点击效果（添加简单的点击反馈，可根据实际需求扩展）
    $('.card - link').click(function () {
        $(this).addClass('active');
        setTimeout(() => {
            $(this).removeClass('active');
        }, 300);
    });
});

$(document).ready(function () {
    // 模拟模块加载逻辑，这里以滚动到一定位置加载模块 1 为例，可按需扩展更多逻辑
    $(window).scroll(function () {
        var scrollTop = $(this).scrollTop();
        if (scrollTop > 200) {
            $('#module-1').addClass('show');
        }
    });

    // 可以添加更多交互逻辑，比如点击某个按钮显示特定模块等
    // 例如，假设页面有个按钮来显示模块 2
    $('#show-module-2-button').click(function () {
        $('#module-2').addClass('show');
    });
});
