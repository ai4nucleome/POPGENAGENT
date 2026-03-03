<template>
    <n-layout-sider 
        class="sidebar-container" 
        collapse-mode="width" 
        :collapsed-width="0" 
        :width="280" 
        show-trigger="bar"
    >
        <div class="flex flex-col h-full bg-gradient-to-b from-white via-white to-slate-50/80">
            <main class="flex flex-col flex-1 min-h-0">
                <!-- Logo area -->
                <div class="px-6 py-5">
                    <div class="flex items-center gap-3">
                        <div class="relative group">
                            <!-- Logo glow effect -->
                            <div class="absolute inset-0 bg-gradient-to-r from-primary-500 to-accent-500 rounded-xl blur-lg opacity-0 group-hover:opacity-40 transition-opacity duration-500"></div>
                            <div class="relative w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500/10 to-accent-500/10 flex items-center justify-center">
                                <img src="../../assets/icon.svg" class="w-6 h-6">
                            </div>
                        </div>
                        <div class="flex flex-col">
                            <span class="text-xl font-bold font-display tracking-tight bg-gradient-to-r from-primary-600 to-accent-600 bg-clip-text text-transparent">
                                PopGenAgent
                            </span>
                            <span class="text-[10px] text-slate-400 font-medium tracking-wider uppercase">Genomics Analysis</span>
                        </div>
                    </div>
                </div>

                <!-- Divider -->
                <div class="mx-5 h-px bg-gradient-to-r from-transparent via-slate-200 to-transparent"></div>

                <!-- New project button -->
                <div class="px-5 py-4">
                    <button 
                        class="group relative w-full overflow-hidden rounded-2xl transition-all duration-300 hover:scale-[1.02] active:scale-[0.98]"
                        @click="onCreateSession"
                    >
                        <!-- Button background -->
                        <div class="absolute inset-0 bg-gradient-to-r from-primary-500 via-accent-500 to-primary-500 bg-[length:200%_100%] group-hover:animate-gradient-x"></div>
                        <!-- Button glow -->
                        <div class="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity bg-gradient-to-r from-primary-400/50 to-accent-400/50 blur-xl"></div>
                        <!-- Button content -->
                        <div class="relative flex items-center justify-between px-5 py-3.5">
                            <div class="flex items-center gap-3">
                                <div class="w-8 h-8 rounded-xl bg-white/20 flex items-center justify-center backdrop-blur-sm">
                                    <Icon icon="ic:round-add" class="text-xl text-white"></Icon>
                                </div>
                                <span class="text-[15px] font-semibold text-white">New Project</span>
                            </div>
                            <div class="w-6 h-6 rounded-lg bg-white/10 flex items-center justify-center">
                                <Icon icon="ic:round-keyboard-command-key" class="text-sm text-white/70"></Icon>
                            </div>
                        </div>
                    </button>
                </div>

                <!-- Project list title -->
                <div class="px-6 py-2">
                    <div class="flex items-center justify-between">
                        <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">Projects</span>
                        <span class="text-xs text-slate-300 bg-slate-100 px-2 py-0.5 rounded-full">{{ pageStore.sessions.length }}</span>
                    </div>
                </div>

                <!-- Project list -->
                <div class="flex-1 min-h-0 pb-4 overflow-hidden">
                    <List />
                </div>
            </main>

        </div> 
    </n-layout-sider>
</template>

<script setup lang="ts">
import { NLayoutSider, useMessage } from "naive-ui";
import List from './List.vue'
import { Icon } from '@iconify/vue'
import { useRouter } from "vue-router";
import usePageStore from "@/store/pageStore";

const pageStore = usePageStore();
const router = useRouter();
const message = useMessage();

async function onCreateSession(){
    try {
        const { session } = await pageStore.createSession();
        pageStore.updateSessions(session.id, session.title);
        pageStore.setCurrentSession(session.id);
        const currentPath = router.currentRoute.value.path.split('/')[2];
        router.push({ path: `/tools/${currentPath}/${session.id}` });
        message.success("Create Success");
    } catch (error) {
        message.error("Create Error");
    }
}
</script>

<style scoped lang="scss">
.sidebar-container {
    :deep(.n-layout-sider-scroll-container) {
        overflow: visible !important;
    }
}

/* Sidebar trigger style */
:deep(.n-layout-toggle-bar) {
    background: linear-gradient(135deg, #3b7ffb, #8a52fc) !important;
    border-radius: 0 8px 8px 0 !important;
    width: 6px !important;
    
    &:hover {
        width: 8px !important;
    }
}

/* Gradient animation */
@keyframes gradient-x {
    0%, 100% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
}

.group:hover .group-hover\:animate-gradient-x {
    animation: gradient-x 2s ease infinite;
}
</style>
