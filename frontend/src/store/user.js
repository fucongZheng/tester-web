import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
    menus: [],
  }),
  actions: {
    setLogin(token, user) {
      this.token = token
      this.user = user
      localStorage.setItem('token', token)
      localStorage.setItem('user', JSON.stringify(user))
    },
    setMenus(menus) {
      this.menus = menus
    },
    logout() {
      this.token = ''
      this.user = null
      this.menus = []
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },
  },
})
