/**
 * sample-pet.js — multi-skin 测试夹具
 * 模拟 techdou-profile 的 pet.js 结构（PET_CONFIG.skins 数组）
 */
const PET_CONFIG = {
  baseSize: 88,
  skins: [
    {
      id: 'techdou',
      name: '科技豆',
      frames: {
        idle: './assets/techdou/idle.webp',
        sleep: './assets/techdou/sleep.webp'
      },
      quotes: ['日拱一卒']
    },
    {
      id: 'douknow',
      name: '豆懂AI',
      frames: {
        idle: './assets/douknow/idle.webp',
        sleep: './assets/douknow/sleep.webp'
      },
      quotes: ['知之为知之']
    }
  ]
};
