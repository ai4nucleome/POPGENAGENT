<template>
    <div class="relative z-10 px-6 py-4">
        <div class="flex items-center justify-center">
            <!-- Left - current project info (fixed width for symmetry) -->
            <div class="flex items-center gap-4 flex-1 min-w-0">
                <div class="hidden md:flex items-center gap-2 px-4 py-2 rounded-xl bg-white/60 backdrop-blur-sm border border-white/50 shadow-soft">
                    <div class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
                    <span class="text-sm font-medium text-slate-600 truncate max-w-[200px]">{{ currentProjectName }}</span>
                </div>
            </div>

            <!-- Center - Agent switch tabs (truly centered) -->
            <div class="flex items-center justify-center flex-shrink-0">
                <div class="relative p-1.5 bg-white/80 backdrop-blur-xl rounded-2xl shadow-soft border border-white/50">
                    <!-- Sliding indicator -->
                    <div 
                        class="absolute top-1.5 h-[calc(100%-12px)] bg-gradient-to-r from-primary-500 to-accent-500 rounded-xl transition-all duration-300 ease-out shadow-glow-sm pointer-events-none"
                        :style="indicatorStyle"
                    ></div>
                    
                    <!-- Tab buttons -->
                    <div class="relative flex">
                        <button
                            v-for="(item, index) in agents" 
                            :key="item.title"
                            :ref="el => itemRefs[index] = el"
                            type="button"
                            class="agent-tab relative z-10 px-5 py-2.5 rounded-xl font-medium text-sm transition-all duration-300 whitespace-nowrap"
                            :class="[
                                item.select 
                                    ? 'text-white' 
                                    : 'text-slate-500 hover:text-slate-700'
                            ]"
                            @click.stop="changeAgentType(item.path)"
                        >
                            <div class="flex items-center gap-2">
                                <component :is="getIcon(item.title)" class="w-4 h-4" />
                                <span>{{ item.title }}</span>
                            </div>
                        </button>
                    </div>
                </div>
            </div>

            <!-- Right - settings button (fixed width for symmetry) -->
            <div class="flex items-center justify-end gap-2 flex-1 min-w-0">
                <button 
                    @click="openSettings"
                    class="p-2.5 rounded-xl bg-white/60 backdrop-blur-sm border border-white/50 shadow-soft hover:bg-white/80 hover:shadow-md transition-all duration-200 group"
                    title="Settings"
                >
                    <Icon icon="solar:settings-bold-duotone" class="w-5 h-5 text-slate-500 group-hover:text-primary-500 transition-colors" />
                </button>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { Icon } from "@iconify/vue"
import { ref, watch, computed, onMounted, nextTick, h } from "vue";
import usePageStore from "@/store/pageStore";
import { useRoute, useRouter } from "vue-router";

const pageStore = usePageStore();
const route = useRoute();
const router = useRouter();
const itemRefs = ref<(HTMLElement | null)[]>([]);

const agents = ref([
    {
        title: "Chat Agent",
        select: false,
        path: "/tools/chat"
    },
    {
        title: "Execute Agent",
        select: false,
        path: "/tools/execute"
    }
    // Analysis Agent temporarily hidden, feature not complete
    // {
    //     title: "Analysis Agent",
    //     select: false,
    //     path: "/tools/analysis"
    // }
])

// Compute current project name
const currentProjectName = computed(() => {
    return pageStore.current_session?.title || 'Select a Project'
})

// Compute sliding indicator style
const indicatorStyle = computed(() => {
    const selectedIndex = agents.value.findIndex(a => a.select);
    if (selectedIndex === -1 || !itemRefs.value[selectedIndex]) {
        return { left: '6px', width: '0px' };
    }
    
    const el = itemRefs.value[selectedIndex];
    if (!el) return { left: '6px', width: '0px' };
    
    return {
        left: `${el.offsetLeft}px`,
        width: `${el.offsetWidth}px`
    };
});

// Get icon component
function getIcon(title: string) {
    const icons: Record<string, any> = {
        'Chat Agent': () => h(Icon, { icon: 'solar:chat-round-dots-bold-duotone' }),
        'Execute Agent': () => h(Icon, { icon: 'solar:code-bold-duotone' })
    };
    return icons[title] || (() => h('span'));
}

const updateAgents = async () => {
    const paths = ["/tools/chat", "/tools/execute"];
    for (let i = 0; i < paths.length; i++) {
        agents.value[i].select = route.path.includes(paths[i]);
    }
    await nextTick();
};

// Open settings panel
function openSettings() {
    pageStore.settings.show = true;
}

onMounted(() => {
updateAgents();
});

watch(() => route.path, () => {
    updateAgents();
});

function changeAgentType(path: string) {
    const currentSession = String(pageStore.current_session?.id || "000");
    router.push({ path: `${path}/${currentSession}` });
}
</script>

<style scoped lang="scss">
/* Agent tab button style */
.agent-tab {
    cursor: pointer;
    user-select: none;
}
</style>
