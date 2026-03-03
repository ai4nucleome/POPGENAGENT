import { createApp } from 'vue'
import App from './App.vue'
import "@/styles/base.css"
import "@/styles/tailMain.css"
import { setupScrollbarStyle } from './plugins'
import router from './router'
import pinia from './store'

async function setup(){
    const startTime = performance.now();
    
    const app = createApp(App);
    
    // Set scrollbar style
    setupScrollbarStyle();
    
    // Register plugins
    app.use(pinia);
    app.use(router);

    // Wait for router to be ready
    await router.isReady();
    
    // Mount app
    app.mount('#app');
    
    // Notify load complete
    window.dispatchEvent(new CustomEvent('app-mounted'));
    
    // Print load time in dev mode
    if (import.meta.env.DEV) {
        console.log(`App mounted in ${(performance.now() - startTime).toFixed(0)}ms`);
    }
}

setup().catch(err => {
    console.error('Failed to start app:', err);
    // Hide loading animation even on error
    window.dispatchEvent(new CustomEvent('app-mounted'));
});
