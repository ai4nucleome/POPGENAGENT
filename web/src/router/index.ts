import { createRouter, createWebHashHistory, RouteRecordRaw } from "vue-router";
import usePageStore from "@/store/pageStore";

// Route components - lazy load
const routes: RouteRecordRaw[] = [
    {
        path: '/popgenagent',
        component: () => import('@/views/popgenagent/Index.vue'),
        name: 'popgenagent',
        meta: { title: 'PopGenAgent', requiresAuth: false }
    },
    {
        path: '/',
        name: 'tools',
        component: () => import('@/views/home/Index.vue'),
        redirect: '/tools/chat',
        meta: { title: 'Tools', requiresAuth: true },
        children: [
            {
                path: '/tools/welcome',
                name: 'welcome',
                component: () => import('@/views/home/welcome/Index.vue'),
                meta: { title: 'Agent' }
            },
            {
                path: '/tools/chat/:uuid?',
                name: 'chat',
                component: () => import('@/views/home/chat/Index.vue'),
                meta: { title: 'Chat Agent' }
            },
            {
                path: '/tools/execute/:uuid?',
                name: 'execute',
                component: () => import('@/views/home/execute/Index.vue'),
                meta: { title: 'Execute Agent' }
            },
            {
                path: '/tools/analysis/:uuid?',
                name: 'analysis',
                component: () => import('@/views/home/analysis/Index.vue'),
                meta: { title: 'Analysis Agent' }
            },
        ]
    },
    {
        path: '/404',
        component: () => import('@/views/404/Index.vue'),
        name: '404',
        meta: { title: 'Error' }
    },
    {
        path: '/:pathMatch(.*)*',
        redirect: '/404',
        name: 'any'
    }
]

const router = createRouter({
    history: createWebHashHistory(),
    routes,
    scrollBehavior: () => ({ left: 0, top: 0 }),
});

// Initialize state tracking
let isInitializing = false;
let initPromise: Promise<void> | null = null;

// Preload common routes
const preloadRoutes = () => {
    // Use requestIdleCallback to preload when idle, don't block first paint
    const preload = () => {
        import('@/views/home/chat/Index.vue');
        import('@/views/home/execute/Index.vue');
        import('@/views/home/analysis/Index.vue');
    };
    
    if ('requestIdleCallback' in window) {
        (window as any).requestIdleCallback(preload, { timeout: 2000 });
    } else {
        setTimeout(preload, 500);
    }
};

router.beforeEach(async (to, from, next) => {
    const pageStore = usePageStore();
    
    // 1. Handle unauthenticated state
    if (!pageStore.token) {
        if (to.path === '/popgenagent') {
            return next();
        }
        return next({ path: '/popgenagent', replace: true });
            }
    
    // 2. Logged in user visiting login page -> redirect
    if (to.path === '/popgenagent') {
        return next({ path: '/tools/chat', replace: true });
    }
    
    // 3. 404 page - allow directly
    if (to.path === '/404') {
                    return next();
                }
    
    // 4. Initialize sessions (only once)
    if (!pageStore._initialized && !isInitializing) {
        isInitializing = true;
        initPromise = pageStore.init().finally(() => {
            isInitializing = false;
            // Preload routes after initialization
            preloadRoutes();
        });
    }
    
    // Wait for initialization to complete
    if (initPromise) {
        await initPromise;
    }
    
    // 5. Handle route params
    const uuid = to.params.uuid as string;
    
    if (uuid) {
        // Has uuid param
        const sessionExists = pageStore.sessions.some(s => String(s.id) === String(uuid));
        if (sessionExists) {
            pageStore.setCurrentSession(uuid);
            return next();
        } else if (pageStore.sessions.length === 0) {
            pageStore.setCurrentSession(uuid);
            return next();
        } else {
            return next({ path: '/404', replace: true });
        }
    }
    
    // 6. No uuid, supplement default session
    const currentSession = pageStore.getCurrentSession();
    const defaultSession = String(currentSession?.id || '000');
            pageStore.setCurrentSession(defaultSession);
    
    // Supplement uuid based on path (use replace to avoid history buildup)
    const pathMap: Record<string, string> = {
        '/tools/chat': `/tools/chat/${defaultSession}`,
        '/tools/execute': `/tools/execute/${defaultSession}`,
        '/tools/analysis': `/tools/analysis/${defaultSession}`,
    };
    
    for (const [prefix, target] of Object.entries(pathMap)) {
        if (to.path === prefix || to.path === `${prefix}/`) {
            return next({ path: target, replace: true });
        }
    }
    
    // Default redirect to chat
    if (to.path === '/' || to.path === '/tools' || to.path === '/tools/') {
        return next({ path: `/tools/chat/${defaultSession}`, replace: true });
        }
    
    next();
});

router.afterEach((to) => {
    // Update page title
    const title = to.meta.title as string;
    if (title) {
        document.title = title;
    }
    
    // Hide loading animation
    const loader = document.getElementById('app-loading');
    if (loader) {
        loader.classList.add('fade-out');
        setTimeout(() => loader.remove(), 500);
    }
});

export default router;
