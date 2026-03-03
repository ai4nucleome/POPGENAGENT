<template>
    <NScrollbar class="px-4">
        <div class="flex flex-col gap-1.5 text-sm">
            <!-- Empty state -->
            <template v-if="!pageStore.sessions.length">
                <div class="flex flex-col items-center py-12 text-center">
                    <div class="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
                        <Icon icon="solar:inbox-bold-duotone" class="text-3xl text-slate-300" />
                    </div>
                    <span class="text-slate-400 font-medium">No projects yet</span>
                    <span class="text-slate-300 text-xs mt-1">Create your first project</span>
                </div>
            </template>
            
            <!-- Project list -->
            <template v-else>
                <div 
                    v-for="(item, index) of pageStore.sessions" 
                    :key="index"
                    class="group"
                >
                    <div 
                        class="relative flex items-center px-4 py-3 rounded-xl cursor-pointer transition-all duration-200"
                        :class="[
                            item.select 
                                ? 'bg-gradient-to-r from-primary-500/10 to-accent-500/10 border border-primary-200/50' 
                                : 'hover:bg-slate-50 border border-transparent'
                        ]"
                        @click="onSessionClick(item)"
                    >
                        <!-- Project icon -->
                        <div 
                            class="w-9 h-9 rounded-xl flex items-center justify-center mr-3 shrink-0 transition-all duration-200"
                            :class="item.select ? 'bg-gradient-to-br from-primary-500 to-accent-500 shadow-sm' : 'bg-slate-100 group-hover:bg-slate-200'"
                        >
                            <Icon 
                                icon="solar:folder-bold-duotone" 
                                class="text-lg transition-colors"
                                :class="item.select ? 'text-white' : 'text-slate-400 group-hover:text-slate-500'"
                            />
                        </div>
                        
                        <!-- Project name -->
                        <div class="relative flex-1 overflow-hidden">
                            <NInput 
                                v-if="item.edit" 
                                v-model:value="item.title" 
                                size="tiny" 
                                class="!bg-white !rounded-lg"
                                @blur="onSaveSession(item)"
                                @keyup.enter="onSaveSession(item)"
                            />
                            <div v-else class="flex flex-col">
                                <span 
                                    class="text-[13px] font-medium truncate transition-colors"
                                    :class="item.select ? 'text-primary-700' : 'text-slate-700'"
                                >
                                    {{ item.title }}
                                </span>
                                <span class="text-[11px] text-slate-400">Project</span>
                            </div>
                        </div>
                        
                        <!-- Action buttons -->
                        <div 
                            class="flex items-center gap-1 transition-all duration-200"
                            :class="item.select ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'"
                        >
                            <template v-if="item.edit">
                                <button 
                                    class="p-1.5 rounded-lg bg-primary-500 hover:bg-primary-600 transition-colors"
                                    @click.stop="onSaveSession(item)"
                                >
                                    <Icon icon="solar:check-circle-bold" class="text-white text-sm"/>
                                </button>
                            </template>
                            <template v-else>
                                <button 
                                    class="p-1.5 rounded-lg hover:bg-white/80 transition-colors"
                                    @click.stop="onEditSession(item)"
                                >
                                    <Icon icon="solar:pen-bold-duotone" class="text-slate-400 hover:text-primary-500 text-sm"/>
                                </button>
                                <button 
                                    class="p-1.5 rounded-lg hover:bg-rose-50 transition-colors"
                                    @click.stop="showAlert=true;"
                                >
                                    <Icon icon="solar:trash-bin-trash-bold-duotone" class="text-slate-400 hover:text-rose-500 text-sm"/>
                                </button>
                            </template>
                        </div>
                    </div>
                </div>
            </template>
        </div>
        <Alert v-model:show="showAlert" @submit="onDeleteSession" />
    </NScrollbar>
</template>

<script setup lang="ts">
import { NScrollbar, NInput, useMessage } from "naive-ui";
import usePageStore from "@/store/pageStore";
import { Icon } from '@iconify/vue'
import { useRouter } from "vue-router";
import Alert from '@/components/Alert.vue'
import { ref } from "vue";

const pageStore = usePageStore();
const router = useRouter();
const message = useMessage();
const showAlert = ref(false);

async function onSessionClick(session: any) {
    pageStore.setCurrentSession(session.id);
    const currentPath = router.currentRoute.value.path.split('/')[2];
    router.push({ path: `/tools/${currentPath}/${session.id}` });
    
    // If on execute page, re-fetch execute info
    if(currentPath === 'execute') {
        await pageStore.getCurrentExecuteInfo();
    }
}

function onEditSession(session: any) {
    session.edit = true;
}

function onSaveSession(session: any) {
    session.edit = false;
    pageStore.updateSessionTitle(session.id, session.title);
    message.success("Update Success");
}

async function onDeleteSession() {
    try {
        const id = pageStore.getCurrentSession().id;
        await pageStore.deleteSession(id)
        message.success("Delete Success")
        pageStore.updateSessions(id)
        onSessionClick(pageStore.getCurrentSession())
    } catch (error) {
        message.error("Delete Error")
    }
}
</script>

<style scoped lang="scss">
/* List item hover effect */
.group:hover .group-hover\:opacity-100 {
    opacity: 1;
}
</style>
