import { computed } from 'vue'
import { useUserStore } from '../store/user'

export function useAdmin() {
  const userStore = useUserStore()
  return { isAdmin: computed(() => userStore.isAdmin) }
}
