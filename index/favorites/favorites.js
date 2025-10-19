Component({
  data: {
    favoriteList: [],
    openid: '',
    isLoading: true,
    hasError: false,
    errorMsg: ''
  },

  lifetimes: {
    attached() {
      this.loadFavorites();
    }
  },

  methods: {
    loadFavorites() {
      const openid = wx.getStorageSync('openid');
      const config = require('../../utils/config.js');

      if (!openid) {
        this.setData({
          isLoading: false,
          hasError: true,
          errorMsg: '请先登录 (´･ω･`)'
        });
        return;
      }

      this.setData({
        isLoading: true,
        hasError: false,
        errorMsg: ''
      });

      wx.request({
        url: `${config.DatabaseConfig.base_url}/api/favorite/get`,
        method: 'POST',
        header: { 'Content-Type': 'application/json' },
        data: { openid },
        success: (res) => {
          this.setData({ isLoading: false });

          if (res.statusCode === 200 && res.data.status === 'success') {
            const ids = res.data.fav_ids || [];
            const names = res.data.fav_names || [];
            const authors = res.data.fav_authors || [];

            const list = ids.map((id, i) => ({
              music_id: id,
              music_name: names[i] || '',
              music_author: authors[i] || ''
            }));

            this.setData({
              favoriteList: list,
              hasError: false
            });

          } else {
            this.setData({
              hasError: true,
              errorMsg: res.data.msg || '加载失败 (；ω；)'
            });
          }
        },
        fail: (err) => {
          this.setData({
            isLoading: false,
            hasError: true,
            errorMsg: `网络错误: ${err.errMsg}`
          });
        }
      });
    },

    onRefresh() {
      this.loadFavorites();
    },

    removeFavorite(e) {
      const music = e.currentTarget.dataset.music;
      const music_id = music.music_id;
      const openid = wx.getStorageSync('openid');
      const config = require('../../utils/config.js');

      wx.request({
        url: `${config.DatabaseConfig.base_url}/api/favorite/remove`,
        method: 'POST',
        header: { 'Content-Type': 'application/json' },
        data: { openid, music_id },
        success: (res) => {
          if (res.data.status === 'success') {
            wx.showToast({ title: '已取消收藏', icon: 'success' });
            this.setData({
              favoriteList: this.data.favoriteList.filter(item => item.music_id !== music_id)
            });
          } else {
            wx.showToast({ title: res.data.msg || '取消收藏失败', icon: 'none' });
          }
        },
        fail: (err) => {
          console.error('取消收藏失败', err);
          wx.showToast({ title: '网络错误', icon: 'none' });
        }
      });
    }
  },

  pageLifetimes: {
    show() {
      this.loadFavorites();
      if (this.getTabBar && this.getTabBar()) {
        this.getTabBar().updateSelected('/index/favorites/favorites');
      }
    }
  }
});
