<template>
    <div class="w-full h-full min-w-4xl">
        <div class="h-full overflow-hidden">
            <n-layout class="absolute w-full h-full" has-sider>
                <n-message-provider :duration="1000">
                            <Slider />
                        </n-message-provider>
                
                <n-layout-content class="main-content" content-style="overflow:hidden;">
                    <!-- Dynamic background layer -->
                    <div class="absolute inset-0 overflow-hidden pointer-events-none">
                        <!-- Gradient background -->
                        <div class="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-primary-50/30"></div>
                        
                        <!-- Grid background -->
                        <div class="absolute inset-0 opacity-[0.4]"
                            style="background-image: radial-gradient(circle at 1px 1px, rgb(226 232 240) 1px, transparent 0); background-size: 32px 32px;">
                        </div>
                        
                        <!-- Dynamic glow -->
                        <div class="absolute top-[-200px] right-[-100px] w-[600px] h-[600px] rounded-full bg-primary-500/[0.07] blur-[100px] animate-pulse-slow"></div>
                        <div class="absolute bottom-[-150px] left-[-100px] w-[500px] h-[500px] rounded-full bg-accent-500/[0.05] blur-[80px] animate-pulse-slow" style="animation-delay: 2s;"></div>
                        <div class="absolute top-[30%] left-[50%] w-[400px] h-[400px] rounded-full bg-cyber-500/[0.03] blur-[60px] animate-float"></div>
                        
                        <!-- Top decoration bar -->
                        <div class="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-primary-500 via-accent-500 to-cyber-500"></div>
                    </div>
                    
                    <div class="relative flex h-full flex-col" style="transform: scale(1);">
                            <Header />
                            <RouterView></RouterView>
                        </div>
                    </n-layout-content>
                </n-layout>
        </div>
        <Settings v-show="pageStore.settings.show" />
        <n-message-provider :duration="1000">
            <AnalysisFiles v-if="pageStore.analysis_files.show"/>
            <ExecuteFiles v-if="pageStore.execute_files.show"/>
        </n-message-provider>
    </div>
</template>

<script setup lang="ts">
import { NLayout, NLayoutContent, NMessageProvider } from "naive-ui";
import Slider from './Slider.vue'
import Header from './Header.vue'
import Settings from '../settings/Index.vue'
import usePageStore from "@/store/pageStore"
import AnalysisFiles from './analysis/files/Files.vue'
import ExecuteFiles from './execute/files/Files.vue'

const pageStore = usePageStore();
</script>

<style scoped lang="scss">
.main-content {
    position: relative;
    background: transparent;
    
    :deep(.n-layout-scroll-container) {
        overflow: hidden;
    }
}

/* Pulse animation */
@keyframes pulse-slow {
    0%, 100% { opacity: 0.5; transform: scale(1); }
    50% { opacity: 0.8; transform: scale(1.1); }
}

.animate-pulse-slow {
    animation: pulse-slow 8s ease-in-out infinite;
}

/* Float animation */
@keyframes float {
    0%, 100% { transform: translateY(0) translateX(0); }
    25% { transform: translateY(-20px) translateX(10px); }
    50% { transform: translateY(0) translateX(20px); }
    75% { transform: translateY(20px) translateX(10px); }
}

.animate-float {
    animation: float 15s ease-in-out infinite;
}
</style>
