<template>
    <Transition name="modal">
        <div class="fixed inset-0 z-50">
            <!-- Background overlay -->
            <div 
                class="absolute inset-0 bg-dark-900/50 backdrop-blur-sm"
                @click="pageStore.settings.show = false"
            ></div>
            
            <!-- Settings panel -->
            <div class="absolute w-[85%] max-w-4xl h-[85%] max-h-[700px] bg-white rounded-2xl shadow-2xl flex overflow-hidden left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 animate-scale-in">
                <!-- Side navigation -->
                <div class="w-[220px] h-full py-6 shrink-0 bg-gradient-to-b from-slate-50 to-white border-r border-slate-100">
                    <!-- Title -->
                    <div class="px-6 mb-6">
                        <h2 class="text-xl font-bold text-slate-800">Settings</h2>
                        <p class="text-sm text-slate-400 mt-1">Configure your workspace</p>
                    </div>
                    
                    <!-- Navigation menu -->
                    <nav class="space-y-1 px-3">
                        <button 
                            v-for="item in menu_list" 
                            :key="item.title"
                            class="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-left transition-all duration-200"
                            :class="[
                                item.select 
                                    ? 'bg-gradient-to-r from-primary-500/10 to-accent-500/10 text-primary-600 border border-primary-200/50' 
                                    : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'
                            ]"
                    @click="onCheck(item)"
                    >
                            <div 
                                class="w-8 h-8 rounded-lg flex items-center justify-center transition-colors"
                                :class="item.select ? 'bg-gradient-to-br from-primary-500 to-accent-500' : 'bg-slate-200'"
                            >
                                <Icon 
                                    :icon="item.icon" 
                                    class="text-lg"
                                    :class="item.select ? 'text-white' : 'text-slate-500'"
                                />
                            </div>
                            <span class="text-sm font-medium">{{ item.title }}</span>
                        </button>
                    </nav>
                </div>
                
                <!-- Content area -->
                <div class="relative flex-1 flex flex-col overflow-hidden">
                    <!-- Top title bar -->
                    <div class="flex items-center justify-between px-8 py-5 border-b border-slate-100">
                        <div>
                            <h3 class="text-lg font-semibold text-slate-800">{{ currentMenu?.title }}</h3>
                            <p class="text-sm text-slate-400">{{ currentMenu?.description }}</p>
                        </div>
                        <button 
                            class="p-2 rounded-xl hover:bg-slate-100 transition-colors"
                            @click="pageStore.settings.show = false"
                        >
                            <Icon icon="solar:close-circle-bold-duotone" class="text-2xl text-slate-400 hover:text-slate-600"/>
                        </button>
            </div>
                    
                    <!-- Settings content -->
                    <div class="flex-1 overflow-auto">
                <n-config-provider :theme-overrides="themeOverrides" class="h-full">
                    <n-message-provider :duration="1000">
                        <n-dialog-provider>
                                    <div class="p-8">
                            <component :is="currentComponent"></component>
                                    </div>
                        </n-dialog-provider>
                    </n-message-provider>
                </n-config-provider>
                    </div>
                </div>
            </div>
        </div>
    </Transition>
</template>

<script setup lang="ts">
import { ref, markRaw, computed } from 'vue';
import { Icon } from "@iconify/vue"
import APISetting from './APISetting.vue'
import ModelSetting from './ModelSetting.vue'
import ExecuteOrNot from './ExecuteOrNot.vue'
import ManageDocs from './ManageDocs.vue'
import ManageTools from './ManageTools.vue'
import UploadData from './UploadData.vue'
import usePageStore from "@/store/pageStore";
import { NConfigProvider, GlobalThemeOverrides, NMessageProvider, NDialogProvider } from 'naive-ui'

const pageStore = usePageStore();
const menu_list = ref([
    {
        title: "API Setting",
        description: "Configure your API keys and endpoints",
        icon: "solar:key-bold-duotone",
        select: true,
        component: markRaw(APISetting)
    },
    {
        title: "Model Setting",
        description: "Choose and configure AI models",
        icon: "solar:cpu-bolt-bold-duotone",
        select: false,
        component: markRaw(ModelSetting)
    },
    {
        title: "Execute Options",
        description: "Configure execution behavior",
        icon: "solar:play-circle-bold-duotone",
        select: false,
        component: markRaw(ExecuteOrNot)
    },
    {
        title: "Manage Docs",
        description: "Manage your documentation library",
        icon: "solar:documents-bold-duotone",
        select: false,
        component: markRaw(ManageDocs)
    },
    {
        title: "Knowledge Base",
        description: "Manage task knowledge entries",
        icon: "solar:book-2-bold-duotone",
        select: false,
        component: markRaw(ManageTools)
    },
    {
        title: "Upload Data",
        description: "Upload files and datasets",
        icon: "solar:upload-bold-duotone",
        select: false,
        component: markRaw(UploadData)
    }
])

const currentComponent = ref(menu_list.value[0].component);
const currentMenu = computed(() => menu_list.value.find(m => m.select));

const themeOverrides: GlobalThemeOverrides = {
    common: {
        primaryColor: '#3b7ffb',
        primaryColorHover: '#549aff',
        primaryColorPressed: '#1751f5',
        borderRadius: '12px',
    },
    Button: {
        textColorHover: "#3b7ffb",
        borderHover: "1px solid #3b7ffb",
        textColorFocus: "#3b7ffb",
        borderFocus: "1px solid #3b7ffb",
        textColorPressed: "#1751f5",
        borderPressed: "1px solid #1751f5",
    },
    Input: {
        borderRadius: '12px',
    }
}

function onCheck(item: any) {
    menu_list.value.forEach(menu => menu.select = false);
    item.select = true;
    currentComponent.value = item.component;
}
</script>

<style scoped lang="scss">
/* Modal scale animation */
.animate-scale-in {
    animation: scaleIn 0.3s ease-out forwards;
}

@keyframes scaleIn {
    from { opacity: 0; transform: translate(-50%, -50%) scale(0.95); }
    to { opacity: 1; transform: translate(-50%, -50%) scale(1); }
}

/* Modal transition */
.modal-enter-active,
.modal-leave-active {
    transition: all 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
    opacity: 0;
}

.modal-enter-from .animate-scale-in,
.modal-leave-to .animate-scale-in {
    transform: translate(-50%, -50%) scale(0.95);
}
</style>
