import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { installSessionHandlers } from './router/session'
import './assets/styles/main.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
installSessionHandlers(router)
app.mount('#app')
