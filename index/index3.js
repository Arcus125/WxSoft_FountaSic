Component({
  data: {
    userInfo: {
      avatarUrl: '',
      nickName: ''
    },
    menuList: [
      { id: 1, title: '收藏', url: '/index/favorites/favorites' },
      { id: 2, title: '留言', url: '' },
      { id: 3, title: '排行', url: '/index/index2' },
      { id: 4, title: '设置', url: '/index/settings/settings' },
    ]
  },

  lifetimes: {
    attached: function() {
      this.loadUserInfo();
    }
  },

  methods: {
    loadUserInfo: function() {
      const app = getApp();
      this.setData({
        'userInfo.avatarUrl': app.globalData.avatarUrl || 'https://mmbiz.qpic.cn/mmbiz/icTdbqWNOwNRna42FI242Lcia07jQodd2FJGIYQfG0LAJGFxM4FbnQP6yfMxBgJ0F3YRqJCJ1aPAK2dQagdusBZg/0',
        'userInfo.nickName': app.globalData.nickname || '用户'
      });
    },


    onMenuItemTap: function(e) {
      const url = e.currentTarget.dataset.url;
      if (url) {
        // 优化：明确tabBar页面使用switchTab，其他页面使用navigateTo
        if (url === '/index/favorites/favorites' || url === '/index/index2' || url === '/index/index' || url === '/index/index3') {
          wx.switchTab({ url: url });
        } else {
          wx.navigateTo({ url: url });
        }
      }
    }
  },

  pageLifetimes: {
    show() {
      this.loadUserInfo();
      if (typeof this.getTabBar === 'function' && this.getTabBar()) {
        this.getTabBar().updateSelected('/index/index3');
      }
    }
  }
})