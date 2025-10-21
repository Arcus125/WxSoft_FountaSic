const app = getApp()
const config = require('../utils/config.js')

Component({
  data: {
    songList: [],        // 所有歌曲
    songIndex: 0,        // 当前选中的索引
    songId: null,        // 当前选中的 song_id
    rankList: [],
    userRank: null,
    userScore: null,
  },

  pageLifetimes: {
    show() {
      this.initSongList()
    }
  },

  methods: {
    /** 初始化歌曲列表并加载默认排行榜 */
    initSongList() {
      const list = app.globalData.allMusicList || []
      if (!list.length) return

      this.setData({
        songList: list,
        songId: list[0].id,   // 默认第一首
        songIndex: 0,
      }, () => {
        this.loadRankData()
      })
    },

    /** Picker选择歌曲变化 */
    onSongChange(e) {
      const index = Number(e.detail.value)
      const selectedSong = this.data.songList[index]

      this.setData({
        songIndex: index,
        songId: selectedSong.id
      }, () => {
        this.loadRankData()
      })
    },

    /** 获取排行榜 (POST) */
    loadRankData() {
      const { songId } = this.data
      if (!songId) return

      wx.request({
        url: `${config.DatabaseConfig.base_url}/api/get_rank`,
        method: 'POST',
        header: { 'Content-Type': 'application/json' },
        data: {
          song_id: songId,
          limit: 50,
          openid: wx.getStorageSync('openid') // 用于返回自己排名（即使不在榜内）
        },
        success: (res) => {
          if (res.statusCode === 200 && res.data.rankList) {
            this.setData({
              rankList: res.data.rankList,
              userRank: res.data.userRank??null,
              userScore: res.data.userScore??null,
            })
          } else {
            wx.showToast({ title: '排行榜获取失败', icon: 'none' })
          }
        },
        fail: () => {
          wx.showToast({ title: '服务器连接失败', icon: 'none' })
        }
      })
    }
  }
})
