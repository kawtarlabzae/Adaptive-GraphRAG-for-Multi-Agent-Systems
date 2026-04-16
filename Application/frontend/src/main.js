import 'vis-network/dist/dist/vis-network.min.css'
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: () => import('./views/HomeView.vue') },
    { path: '/session/:id', component: () => import('./views/SessionView.vue') },
    { path: '/aero/:id',    component: () => import('./views/AeroSessionView.vue') },
    { path: '/general/:id', component: () => import('./views/GeneralSessionView.vue') },
  ]
})

const pinia = createPinia()
const app = createApp(App)
app.use(pinia)
app.use(router)
app.mount('#app')
