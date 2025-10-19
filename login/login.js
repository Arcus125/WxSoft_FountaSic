Page({
  data: {
    avatarUrl: '',
    nickname: '',
    openid: '',
  },
  onLoad(options) {
    const app = getApp();
    const cachedOpenid = wx.getStorageSync('openid');
    if (cachedOpenid) {
      console.log('发现缓存的openid:', cachedOpenid);
      app.globalData.openid = cachedOpenid;
      app.globalData.avatarUrl = wx.getStorageSync('avatarUrl');
      app.globalData.nickname = wx.getStorageSync('nickname');
      wx.switchTab({ url: '/index/index' });
      return;
    }
    wx.showLoading({ title: '加载中...', mask: true });
    wx.login({
      success: (res) => {
        if (res.code) {
          this.sendCodeToServer(res.code, '/api/login');
        }
      }
    });
  },
  onNicknameInput(e) {
    this.setData({ nickname: e.detail.value });
  },
  onChooseAvatar(e) {
    this.setData({ avatarUrl: e.detail.avatarUrl });
  },
  TapLogin(e) {
    console.log('开始注册流程');
    wx.showLoading({ title: '注册中...', mask: true });
    wx.login({
      success: (res) => {
        if (res.code) {
          this.sendCodeToServer(res.code, '/api/register');
        }
      }
    });
  },
  sendCodeToServer(code, methon) {
    const config = require('../utils/config.js');
    wx.request({
      url: config.DatabaseConfig.base_url + methon,
      method: 'POST',
      data: {
        code,
        nickname: this.data.nickname,
        avatarUrl: this.data.avatarUrl,
      },
      header: { 'Content-Type': 'application/json' },
      success: (res) => {
        console.log("服务器响应:", res.data);
        wx.hideLoading();
        if (res.data.status === 'success') {
          const { openid, avatar_url, nickname } = res.data;
          wx.setStorageSync('openid', openid);
          wx.setStorageSync('avatarUrl', avatar_url);
          wx.setStorageSync('nickname', nickname);
          const app = getApp();
          app.globalData.openid = openid;
          app.globalData.avatarUrl = avatar_url;
          app.globalData.nickname = nickname;
          wx.switchTab({ url: '/index/index' });
        } else {
          wx.showToast({ title: '请注册', icon: 'none' });
        }
      },
      fail: (error) => {
        wx.hideLoading();
        console.error('请求失败:', error);
        wx.showToast({ title: '网络请求失败', icon: 'none' });
      }
    });
  }
})
