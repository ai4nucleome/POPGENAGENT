<template>
    <div class="w-full h-full overflow-hidden">
        <div class="flex flex-col max-w-4xl m-auto h-full">
            <!-- Message area -->
            <main class="p-4 flex-1 overflow-hidden box-border">
                <div id="scrollRef" ref="scrollRef" class="h-full overflow-hidden overflow-y-auto box-border scroll-smooth">
                    <div id="image-wrapper" class="w-full max-w-screen-xl m-auto px-4 py-6 box-border">
                        <!-- Empty state -->
                        <div v-if="initial && pageStore.current_session && pageStore.current_session.analysis_info && pageStore.current_session.analysis_info.length == 0" class="animate-fade-in">
                            <div class="text-center mb-8">
                                <h2 class="text-3xl font-bold mb-3">
                                    <span class="bg-gradient-to-r from-primary-600 via-accent-600 to-cyber-600 bg-clip-text text-transparent">
                                        Analysis Agent
                                    </span>
                                </h2>
                                <p class="text-slate-500">Interactive demographic modeling with advanced tools</p>
                            </div>
                            
                            <div class="max-w-2xl mx-auto mb-10">
                                <div class="bg-white/60 backdrop-blur-sm rounded-2xl p-6 border border-slate-200/50 shadow-soft">
                                    <div class="text-slate-600 leading-relaxed text-sm" v-html="defaultMessage"></div>
                                </div>
                            </div>
                            
                            <div class="flex items-center justify-center">
                                <div class="relative">
                                    <div class="absolute inset-0 bg-gradient-to-r from-primary-500/20 to-accent-500/20 rounded-full blur-2xl"></div>
                                    <video muted autoplay loop class="relative object-cover w-32 h-32 pointer-events-none rounded-2xl" src="../../../assets/single-loop.mp4"></video>
                        </div>
                            </div>
                        </div>
                        
                        <!-- Message list -->
                        <template v-else-if="initial">
                            <Message 
                                v-for="(item, index) in pageStore.current_session.analysis_info" 
                                :key="index"
                                :text="item.text" 
                                :inversion="item.author == 'user' ? true : false" 
                                :generate="false"
                            />
                        </template>
                    </div>
                </div>
            </main>
            
            <!-- Input area -->
            <footer class="p-4 box-border">
                <div class="w-full max-w-screen-xl m-auto">
                    <div class="relative">
                        <div class="absolute -inset-1 bg-gradient-to-r from-primary-500/10 via-accent-500/10 to-cyber-500/10 rounded-2xl blur-lg opacity-0 transition-opacity duration-300" :class="{ 'opacity-100': isFocused }"></div>
                        
                        <div class="relative bg-white/90 backdrop-blur-xl rounded-2xl shadow-soft border border-slate-200/50 transition-all duration-300" :class="{ 'border-primary-300/50 shadow-md': isFocused }">
                            <div class="flex items-end gap-3 px-4 py-3">
                                <div class="flex-1 space-y-3">
                            <NInput
                                ref="inputRef"
                                v-model:value="userInput"
                                type="textarea"
                                        placeholder="Describe your demographic modeling task..."
                                :autosize="{ minRows: 1, maxRows: 4 }"
                                @keypress="handleEnter"
                                        @focus="isFocused = true"
                                        @blur="isFocused = false"
                                :disabled="generate"
                                        class="!bg-transparent"
                                    />
                                    
                                    <!-- File selection area -->
                                    <div class="flex items-center gap-2 pt-2 border-t border-slate-100">
                                        <button 
                                            class="group flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-50 hover:bg-slate-100 transition-all duration-200"
                                            @click="pageStore.analysis_files.show = true;"
                                        >
                                            <Icon icon="solar:add-folder-bold-duotone" class="text-lg text-slate-400 group-hover:text-primary-500 transition-colors"></Icon>
                                            <span class="text-sm text-slate-500 group-hover:text-slate-700">Add Files</span>
                                        </button>
                                        
                                        <div ref="dataPathRef" class="flex flex-wrap gap-2 flex-1">
                                            <div 
                                                v-for="id in pageStore.analysis_files.selects" 
                                                :key="id" 
                                                class="flex items-center gap-2 px-3 py-1.5 bg-primary-50 text-primary-600 rounded-lg text-sm"
                                            >
                                                <Icon icon="solar:file-bold-duotone" class="text-sm"></Icon>
                                                <span class="truncate max-w-[150px]">{{ getFilename(id) }}</span>
                                                <button 
                                                    class="hover:bg-primary-100 rounded p-0.5 transition-colors"
                                                    @click="deleteOption(id)"
                                                >
                                                    <Icon icon="solar:close-circle-bold" class="text-sm text-primary-400 hover:text-primary-600"></Icon>
                                                </button>
                                    </div>
                                </div>
                                    </div>
                                </div>
                                <SendButton :disabled="generate" @send="handleSubmit"/>
                            </div>
                        </div>
                    </div>
                    
                    <p class="text-center text-xs text-slate-400 mt-3">
                        AnalysisAgent enables interactive demographic modeling with FastSimCoal
                    </p>
                </div>
            </footer>
        </div>
    </div>
</template>

<script setup lang="ts">
import { NInput } from 'naive-ui'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import SendButton from '../../../components/SendButton.vue';
import Message from '../../../components/Message.vue'
import { useScroll } from '../hooks/useScroll'
import { useRoute, useRouter } from "vue-router";
import usePageStore from "@/store/pageStore";
import { Icon } from '@iconify/vue';

const { scrollRef, scrollToBottom } = useScroll()
const userInput = ref("");
const isFocused = ref(false);
const route = useRoute();
const router = useRouter();
const initial = ref(false);
const pageStore = usePageStore();
const defaultText = `<strong>AnalysisAgent</strong> enables interactive demographic modeling with tools like FastSimCoal. It can help you:
<br/><br/>
• Design demographic models<br/>
• Run coalescent simulations<br/>
• Parameter estimation<br/>
• Model comparison and selection`;
const defaultMessage = ref("");
let defaultMessageTimer = -1;
const generate = ref(false);
const dataPathRef = ref<HTMLDivElement>()
let processingCheckInterval: number | null = null;

async function checkProcessingStatus() {
    if (generate.value) {
        try {
            const wasGenerating = generate.value;
            await pageStore.getCurrentAnalysisInfo();
            
            const hasProcessingMessage = pageStore.current_session.analysis_info.some(item => item.generate);
            
            if (wasGenerating && !hasProcessingMessage) {
                generate.value = false;
                nextTick(() => {
                    scrollToBottom();
                });
                
                if (processingCheckInterval) {
                    clearInterval(processingCheckInterval);
                    processingCheckInterval = null;
                }
            }
        } catch (error) {
            console.error('Error checking analysis processing status:', error);
        }
    }
}

function startProcessingCheck() {
    if (processingCheckInterval) {
        clearInterval(processingCheckInterval);
    }
    processingCheckInterval = setInterval(checkProcessingStatus, 2000);
}

watch(() => route.path, (_new, _old) => {
    if (route.path.includes("/tools/analysis/")) {
        if (!_old.includes("000")) updateChat();
    }
});

onMounted(() => {
    updateChat();
})
onBeforeUnmount(() => {
    clearInterval(defaultMessageTimer);
    if (processingCheckInterval) {
        clearInterval(processingCheckInterval);
        processingCheckInterval = null;
    }
})

function getFilename(id: number) {
    return pageStore.analysis_files.files.find(file => file.id == id)?.filename || "undefined";
}
function getAbsolutePath(id: number) {
    return pageStore.analysis_files.files.find(file => file.id == id)?.absolute_path || "undefined";
}

async function updateChat() {
    pageStore.analysis_files.selects = [];
    defaultMessage.value = "";
    userInput.value = "";
    clearInterval(defaultMessageTimer);
    initial.value = false;
    generate.value = false;
    
    // Use requestAnimationFrame to delay data loading so UI renders first
    requestAnimationFrame(async () => {
    try {
        await pageStore.getCurrentAnalysisInfo();
        if (!pageStore.current_session.analysis_info.length) {
            const texts = defaultText.split(" ");
            const textsLength = texts.length;
            let index = 0;
            defaultMessageTimer = setInterval(() => {
                index++;
                defaultMessage.value = texts.slice(0, index).join(" ");
                if (index >= textsLength) {
                    clearInterval(defaultMessageTimer);
                }
            }, 50) as unknown as number;
        }
        else {
            nextTick(() => {
                scrollToBottom();
            })
            
            const hasProcessingMessage = pageStore.current_session.analysis_info.some(item => item.generate);
            if (hasProcessingMessage) {
                generate.value = true;
                startProcessingCheck();
            }
        }
    } catch (error) { /* Ignore initialization errors */ }
    initial.value = true;
    });
}

// Analysis Agent does not need stop functionality, cancelRequest removed

function handleEnter(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        handleSubmit();
    }
}

function deleteOption(id: number) {
    pageStore.analysis_files.selects = pageStore.analysis_files.selects.filter(_id => _id != id);
}

async function handleSubmit() {
    if (userInput.value) {
        const text = userInput.value;
        const title_length = 30;
        const title = text.slice(0, Math.min(title_length, text.length));
        if (!pageStore.sessions.length) {
            const { session } = await pageStore.createSession(title);
            pageStore.updateSessions(session.id, session.title);
            pageStore.setCurrentSession(session.id);
            const currentPath = router.currentRoute.value.path.split('/')[2];
            router.push({ path: `/tools/${currentPath}/${session.id}` });
        }
        if (pageStore.getCurrentSession().title.includes("New Session") || pageStore.getCurrentSession().title.includes("Untitled Session")) {
            await pageStore.updateSessionTitle(pageStore.getCurrentSession().id, title);
        }

        const files: string[] = [];
        for (let i = 0; i < pageStore.analysis_files.selects.length; i++) {
            files.push(getAbsolutePath(pageStore.analysis_files.selects[i]))
        }

        pageStore.addCurrentAnalysisInfo("user", text, false);
        pageStore.addCurrentAnalysisInfo("computer", "thinking...", false);
        userInput.value = "";
        pageStore.analysis_files.selects = [];
        scrollToBottom();
        nextTick(() => {
            generate.value = true;
            startProcessingCheck();
        })
        
        pageStore.receiveAnalysisMessageFromServer(text, files, (t: string) => {
            pageStore.updateCurrentAnalysisInfo(t, false);
            scrollToBottom();
            generate.value = false;
        })
    }
    return;
}
</script>

<style scoped lang="scss">
:deep(.n-input) {
    --n-border: none !important;
    --n-border-hover: none !important;
    --n-border-focus: none !important;
    --n-box-shadow-focus: none !important;
    background: transparent !important;
}

.animate-fade-in {
    animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>
