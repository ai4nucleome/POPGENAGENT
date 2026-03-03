<template>
    <div class="w-full h-full overflow-hidden">
        <div class="flex flex-col max-w-4xl m-auto h-full">
            <!-- Message area -->
            <main class="p-4 flex-1 overflow-hidden box-border">
                <div id="scrollRef" ref="scrollRef" class="h-full overflow-hidden overflow-y-auto box-border scroll-smooth">
                    <div id="image-wrapper" class="w-full max-w-screen-xl m-auto px-4 py-6 box-border">
                        <!-- Empty state - welcome page -->
                        <div v-if="initial && pageStore.current_session && pageStore.current_session.chat_info && pageStore.current_session.chat_info.length == 0" class="animate-fade-in">
                            <!-- Welcome title -->
                            <div class="text-center mb-8">
                                <h2 class="text-3xl font-bold mb-3">
                                    <span class="bg-gradient-to-r from-primary-600 via-accent-600 to-cyber-600 bg-clip-text text-transparent">
                                        Hello, Researcher
                                    </span>
                                </h2>
                                <p class="text-slate-500">How can I assist your genomics analysis today?</p>
                            </div>
                            
                            <!-- Introduction text -->
                            <div class="max-w-2xl mx-auto mb-10">
                                <div class="bg-white/60 backdrop-blur-sm rounded-2xl p-6 border border-slate-200/50 shadow-soft">
                                    <div class="text-slate-600 leading-relaxed text-sm" v-html="defaultMessage"></div>
                                </div>
                            </div>
                            
                            <!-- Animation - same video as Execute -->
                            <div class="flex items-center justify-center">
                                <div class="relative">
                                    <div class="absolute inset-0 bg-gradient-to-r from-primary-500/20 to-accent-500/20 rounded-full blur-2xl"></div>
                                    <video muted autoplay loop class="relative object-cover w-32 h-32 pointer-events-none rounded-2xl" src="../../../assets/single-loop.mp4"></video>
                                </div>
                            </div>
                            
                            <!-- Quick question suggestions -->
                            <div class="mt-10 grid grid-cols-2 gap-3 max-w-2xl mx-auto">
                                <button 
                                    v-for="suggestion in suggestions" 
                                    :key="suggestion.text"
                                    class="group p-4 rounded-xl bg-white/80 hover:bg-white border border-slate-200/50 shadow-soft hover:shadow-md transition-all duration-200 text-left"
                                    @click="useSuggestion(suggestion.text)"
                                >
                                    <div class="flex items-start gap-3">
                                        <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500/10 to-accent-500/10 flex items-center justify-center shrink-0">
                                            <Icon :icon="suggestion.icon" class="text-primary-500 text-lg" />
                                        </div>
                                        <div>
                                            <p class="text-sm font-medium text-slate-700 group-hover:text-primary-600 transition-colors">{{ suggestion.text }}</p>
                                        </div>
                        </div>
                                </button>
                            </div>
                        </div>
                        
                        <!-- Message list -->
                        <template v-else-if="initial">
                            <Message 
                                v-for="(item, index) in pageStore.current_session.chat_info" 
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
                        <!-- Input box glow -->
                        <div class="absolute -inset-1 bg-gradient-to-r from-primary-500/10 via-accent-500/10 to-cyber-500/10 rounded-2xl blur-lg opacity-0 transition-opacity duration-300" :class="{ 'opacity-100': isFocused }"></div>
                        
                        <!-- Input box container -->
                        <div class="relative flex items-end gap-3 px-4 py-3 bg-white/90 backdrop-blur-xl rounded-2xl shadow-soft border border-slate-200/50 transition-all duration-300" :class="{ 'border-primary-300/50 shadow-md': isFocused }">
                        <NInput
                            ref="inputRef"
                            v-model:value="userInput"
                            type="textarea"
                                placeholder="Ask anything about population genetics..."
                            :autosize="{ minRows: 1, maxRows: 4 }"
                            @keypress="handleEnter"
                                @focus="isFocused = true"
                                @blur="isFocused = false"
                            :disabled="generate"
                                class="flex-1 !bg-transparent"
                            />
                            <SendButton :disabled="generate || !userInput.trim()" @send="handleSubmit"/>
                        </div>
                    </div>
                    
                    <!-- Bottom hint -->
                    <p class="text-center text-xs text-slate-400 mt-3">
                        Press <kbd class="px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 font-mono text-[10px]">Enter</kbd> to send, 
                        <kbd class="px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 font-mono text-[10px]">Shift + Enter</kbd> for new line
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

const suggestions = [
    { text: "What is population genetics?", icon: "solar:question-circle-bold-duotone" },
    { text: "Explain PCA analysis for genomics", icon: "solar:chart-bold-duotone" },
    { text: "How to perform quality control?", icon: "solar:shield-check-bold-duotone" },
    { text: "Calculate F-statistics", icon: "solar:calculator-bold-duotone" }
];

const defaultText = `<strong>PopGenAgent</strong> is an AI-powered agent system designed for population genetics analysis. Starting from raw genotype data across individuals or populations, PopGenAgent helps you perform essential tasks like:
<br/><br/>
• <strong>Quality Control</strong> & Relatedness Filtering<br/>
• <strong>smartPCA</strong> Analysis<br/>
• <strong>F-statistics</strong> (f2/f3/f4/D statistics)<br/>
• <strong>LD Decay</strong> & ROH Analysis<br/>
• <strong>Treemix</strong> Analysis`;

const defaultMessage = ref("");
let defaultMessageTimer = -1;
const generate = ref(false);
let processingCheckInterval: number | null = null;

function useSuggestion(text: string) {
    userInput.value = text;
    handleSubmit();
}

async function checkProcessingStatus() {
    if (generate.value) {
        try {
            const wasGenerating = generate.value;
            await pageStore.getCurrentChatInfo();
            
            const hasProcessingMessage = pageStore.current_session.chat_info.some(item => item.generate);
            
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
            console.error('Error checking processing status:', error);
        }
    }
}

function startProcessingCheck() {
    if (processingCheckInterval) {
        clearInterval(processingCheckInterval);
    }
    processingCheckInterval = setInterval(checkProcessingStatus, 2000) as unknown as number;
}

watch(() => route.path, (_new, _old) => {
    if (route.path.includes("/tools/chat/")) {
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

async function updateChat() {
    defaultMessage.value = "";
    userInput.value = "";
    clearInterval(defaultMessageTimer);
    initial.value = false;
    generate.value = false;
    try {
        await pageStore.getCurrentChatInfo();
        
        const hasProcessingMessage = pageStore.current_session.chat_info.some(item => item.generate);
        if (hasProcessingMessage) {
            generate.value = true;
            startProcessingCheck();
        }
        
        if (!pageStore.current_session.chat_info.length) {
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
        }
    } catch (error) {
        // Handle error
    }
    initial.value = true;
}

// Chat Agent does not need stop functionality, cancelRequest removed

function handleEnter(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        handleSubmit();
    }
}

async function handleSubmit() {
    if (userInput.value && userInput.value.trim()) {
        const text = userInput.value;
        const title_length = 30;
        const title = text.slice(0, Math.min(title_length, text.length));
        
        if (!pageStore.sessions.length) {
            try {
                const { session } = await pageStore.createSession(title);
                pageStore.updateSessions(session.id, session.title);
                pageStore.setCurrentSession(session.id);
                const currentPath = router.currentRoute.value.path.split('/')[2];
                router.push({ path: `/tools/${currentPath}/${session.id}` });
            } catch (error) {
                return;
            }
        }
        
        const currentSession = pageStore.getCurrentSession();
        
        if (currentSession.title && (currentSession.title.includes("New Session") || currentSession.title.includes("Untitled Session"))) {
            await pageStore.updateSessionTitle(currentSession.id, title);
        }
        
        pageStore.addCurrentChatInfo("user", text, false);
        pageStore.addCurrentChatInfo("computer", "thinking...", false);
        userInput.value = "";
        scrollToBottom();
        generate.value = true;
        
        pageStore.receiveMessageFromServer(text, (t: string) => {
            pageStore.updateCurrentChatInfo(t, false);
            scrollToBottom();
            generate.value = false;
        })
    }
}
</script>

<style scoped lang="scss">
/* Input box style optimization */
:deep(.n-input) {
    --n-border: none !important;
    --n-border-hover: none !important;
    --n-border-focus: none !important;
    --n-box-shadow-focus: none !important;
    background: transparent !important;
}

:deep(.n-input__textarea-el) {
    font-size: 15px !important;
    line-height: 1.6 !important;
}

/* Fade-in animation */
.animate-fade-in {
    animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
</style>
