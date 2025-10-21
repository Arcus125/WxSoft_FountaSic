const app = getApp();
Component({
  data: {
    mode: 'single',
    rankList: [],
    userRank: null,
    userScore: null
  },

  pageLifetimes: {
    show() {
      if (typeof this.getTabBar === 'function' && this.getTabBar()) {
        this.getTabBar().updateSelected('/index/index2');
      }
      this.loadRankData();
    }
  },

  methods: {
    setMode(e) {
      const mode = e.currentTarget.dataset.mode;
      this.setData({ mode });
      this.loadRankData();
    },

    // ======== 改成 POST 获取排行榜 ========
    loadRankData() {
      const { mode } = this.data;
      const config = require('../utils/config.js');

      wx.request({
        url: `${config.DatabaseConfig.base_url}/api/get_rank`,
        method: 'POST',
        header: { 'Content-Type': 'application/json' },
        data: { mode, limit: 50 },
        success: (res) => {
          if (res.statusCode === 200 && res.data.rankList) {
            const openid = wx.getStorageSync('openid');
            let userRank = null, userScore = null;
            
            const entry = res.data.rankList.find(r => r.openid === openid);
            if (entry) {
              userRank = entry.rank;
              userScore = entry.score;
            }

            this.setData({ rankList: res.data.rankList, userRank, userScore });

            if (res.data.rankList.length === 0) {
              wx.showToast({ title: '暂无排行榜数据', icon: 'none' });
            }
          } else {
            wx.showToast({ title: '获取排行榜失败', icon: 'none' });
          }
        },
        fail: () => wx.showToast({ title: '服务器连接失败', icon: 'none' })
      });
    },

    // ======== 修正 uploadScore 请求路径 ========
    uploadScore(score, mode) {
      const config = require('../utils/config.js');
      const openid = wx.getStorageSync('openid');
      if (!openid) return;

      wx.request({
        url: `${config.DatabaseConfig.base_url}/api/upload_rank`,
        method: 'POST',
        header: { 'Content-Type': 'application/json' },
        data: {
          openid,
          nickname: wx.getStorageSync('nickname') || '匿名用户',
          avatar_url: wx.getStorageSync('avatarUrl') || '',
          mode,
          score
        },
        success: res => console.log('成绩上传成功:', res.data),
        fail: err => console.error('成绩上传失败:', err)
      });
    }
  }
})
