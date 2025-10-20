Page({
  data: {
    favoriteList: [],
    openid: '',
    isLoading: true,
    hasError: false,
    errorMsg: ''
  },

  onShow() {
    this.loadFavorites();
  },

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

          // 组合成 favoriteList = [{music_id, music_name, music_author},...]
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
  }
})
