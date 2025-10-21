const config=require('./utils/config.js');
App({
  globalData: {
    avatarUrl: '',
    nickname: '',
    openid: '',
    apiBaseUrl: config.DatabaseConfig.base_url,
    allMusicList: [
      { id: 1, name: "死别", author: "在虚无中永存/rnb脑袋", duration: "2:13" },
      { id: 2, name: "肖邦：降E大调夜曲, Op. 9 No. 2", author: "土星皇家交响乐团", duration: "3:54" },
      { id: 3, name: "肖斯塔科维奇：第二圆舞曲", author: "土星皇家交响乐团", duration: "3:44" },
      { id: 4, name: "Cogwork Core", author: "Christopher Larkin", duration: "1:30" },
      { id: 5, name: "讨厌红楼梦", author: "陶喆", duration: "4:02" },
      { id: 6, name: "找自己", author: "陶喆", duration: "5:04" },
      { id: 7, name: "才二十三", author: "方大同", duration: "3:44" },
      { id: 8, name: "红豆", author: "方大同", duration: "3:56" },
      { id: 9, name: "君の胸にLaLaLa", author: "MADOKA", duration: "3:38" },
      { id: 10, name: "Downfall", author: "Brian Cheng", duration: "4:39" }
    ],
  },

  onLaunch() {
    console.log('ヽ(●´∀`●)ﾉ Fountasic App Launch')
    
    // 检查登录状态
    const openid = wx.getStorageSync('openid')
    if (openid) {
      this.globalData.openid = openid
      this.globalData.avatarUrl = wx.getStorageSync('avatarUrl') || ''
      this.globalData.nickname = wx.getStorageSync('nickname') || ''
      console.log(' 用户已登录～(￣▽￣～)~:', this.globalData.nickname)
    }
  },

  onShow() {
    console.log('ヾ(◍°∇°◍)ﾉﾞ App Show')
  },

  onHide() {
    console.log('(๑•̀ㅂ•́)و✧ App Hide')
  }
})