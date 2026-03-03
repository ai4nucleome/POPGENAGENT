<template>
    <div 
        ref="messageRef" 
        class="flex w-full mb-6 overflow-hidden animate-slide-up" 
        :class="[{ 'flex-row-reverse': props.inversion }]"
    >
        <!-- Avatar -->
        <div 
            class="flex items-start justify-center flex-shrink-0 overflow-hidden"
            :class="[inversion ? 'ml-3' : 'mr-3']"
        >
            <Avatar :is-user="!inversion" />
        </div>
        
        <!-- Message content area -->
        <div class="overflow-hidden flex-1 max-w-[85%]" :class="[inversion ? 'items-end' : 'items-start']">
            <div class="flex items-end gap-2" :class="[inversion ? 'flex-row-reverse' : 'flex-row']">
                <div class="relative group">
                    <div 
                        v-if="inversion" 
                        class="absolute -inset-1 bg-gradient-to-r from-primary-500/20 to-accent-500/20 rounded-2xl blur opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                    ></div>
                <Text ref="textRef" :inversion="inversion" :text="text" :as-raw-text="asRawText" :generate="generate"/>
                </div>
            </div>
            
            <!-- Execute Plan button -->
            <div v-if="index == total - 1 && type == 'plan'" class="flex items-center gap-3 mt-4">
                <button 
                    class="group flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-primary-500 to-accent-500 hover:shadow-lg hover:shadow-primary-500/30 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
                    @click="executePlan"
                >
                    <Icon icon="solar:play-bold" class="text-white text-lg"></Icon>
                    <span class="font-semibold text-white">Execute Plan</span>
                </button>
                <button 
                    class="group flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white border border-slate-200 hover:border-primary-300 hover:bg-primary-50 transition-all duration-200"
                    @click="openPlanEditor"
                >
                    <Icon icon="solar:pen-bold-duotone" class="text-slate-500 group-hover:text-primary-500 text-lg"></Icon>
                    <span class="font-medium text-slate-600 group-hover:text-primary-600">Edit Plan</span>
                </button>
            </div>
            
            <!-- Stop button -->
            <div v-if="index == total - 1 && canStop" class="mt-4">
                <button 
                    class="group flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-50 hover:bg-rose-100 border border-rose-200 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                    :disabled="isStopping"
                    @click="handleStop"
                >
                    <template v-if="isStopping">
                        <div class="w-4 h-4 rounded-full border-2 border-rose-400 border-t-transparent animate-spin"></div>
                        <span class="text-sm font-medium text-rose-600">Stopping...</span>
                    </template>
                    <template v-else>
                    <div class="w-4 h-4 rounded-full border-2 border-rose-400 flex items-center justify-center">
                        <div class="w-1.5 h-1.5 rounded-sm bg-rose-500"></div>
                    </div>
                    <span class="text-sm font-medium text-rose-600">Stop Execution</span>
                    </template>
                </button>
            </div>
            
            <!-- Paused/Error state buttons -->
            <div v-if="index == total - 1 && (type == 'paused' || type == 'error')" class="flex items-center gap-3 mt-4">
                <button 
                    class="group flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 hover:shadow-lg hover:shadow-emerald-500/30 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
                    @click="executePlan"
                >
                    <Icon icon="solar:play-bold" class="text-white text-lg"></Icon>
                    <span class="font-semibold text-white">Resume</span>
                </button>
                <button 
                    class="group flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white border border-slate-200 hover:border-amber-300 hover:bg-amber-50 transition-all duration-200"
                    @click="openStepsEditor"
                >
                    <Icon icon="solar:settings-bold-duotone" class="text-slate-500 group-hover:text-amber-500 text-lg"></Icon>
                    <span class="font-medium text-slate-600 group-hover:text-amber-600">Edit Steps</span>
                </button>
            </div>
            
            <!-- Report button -->
            <div v-if="index == total - 1 && type == 'finish'" class="mt-4">
                <button 
                    class="group flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-violet-500 to-purple-500 hover:shadow-lg hover:shadow-violet-500/30 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
                    @click="onGenerateReport"
                >
                    <Icon icon="solar:document-text-bold" class="text-white text-lg"></Icon>
                    <span class="font-semibold text-white">Generate Report</span>
                </button>
            </div>
        </div>
    </div>
    
    <!-- Plan editor modal -->
    <Teleport to="body">
        <Transition name="modal">
            <div v-if="showPlanEditor" class="fixed inset-0 z-50 flex items-center justify-center p-4">
                <div class="absolute inset-0 bg-dark-900/60 backdrop-blur-sm" @click="showPlanEditor = false"></div>
                <div class="relative w-full max-w-3xl max-h-[80vh] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-scale-in">
                    <!-- Header -->
                    <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
                        <div class="flex items-center gap-3">
                            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500/10 to-accent-500/10 flex items-center justify-center">
                                <Icon icon="solar:pen-bold-duotone" class="text-primary-500 text-xl"/>
                            </div>
                            <div>
                                <h3 class="text-lg font-semibold text-slate-800">Edit Plan</h3>
                                <p class="text-sm text-slate-400">Modify the execution plan</p>
                            </div>
                        </div>
                        <button 
                            class="p-2 rounded-xl hover:bg-slate-100 transition-colors"
                            @click="showPlanEditor = false"
                        >
                            <Icon icon="solar:close-circle-bold-duotone" class="text-2xl text-slate-400 hover:text-slate-600"/>
                        </button>
                    </div>
                    <!-- Content -->
                    <div class="flex-1 p-6 overflow-auto">
                        <textarea 
                            v-model="tempPlan" 
                            class="w-full h-full min-h-[300px] p-4 bg-slate-50 rounded-xl border border-slate-200 focus:border-primary-300 focus:ring-2 focus:ring-primary-100 resize-none font-mono text-sm transition-all"
                            placeholder="Enter plan JSON..."
                        ></textarea>
                    </div>
                    <!-- Footer -->
                    <div class="flex justify-end gap-3 px-6 py-4 border-t border-slate-100 bg-slate-50/50">
                        <button 
                            class="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 transition-colors"
                            @click="showPlanEditor = false"
                        >
                            Cancel
                        </button>
                        <button 
                            class="px-6 py-2 rounded-xl bg-gradient-to-r from-primary-500 to-accent-500 text-white font-medium hover:shadow-lg hover:shadow-primary-500/30 transition-all"
                            @click="savePlan"
                        >
                            Save Changes
                        </button>
                </div>
                </div>
            </div>
        </Transition>
    </Teleport>
    
    <!-- Steps editor modal -->
    <Teleport to="body">
        <Transition name="modal">
            <div v-if="showStepsEditor" class="fixed inset-0 z-50 flex items-center justify-center p-4">
                <div class="absolute inset-0 bg-dark-900/60 backdrop-blur-sm" @click="showStepsEditor = false"></div>
                <div class="relative w-full max-w-3xl max-h-[80vh] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-scale-in">
                    <!-- Header -->
                    <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
                        <div class="flex items-center gap-3">
                            <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-500/10 to-orange-500/10 flex items-center justify-center">
                                <Icon icon="solar:settings-bold-duotone" class="text-amber-500 text-xl"/>
                            </div>
                            <div>
                                <h3 class="text-lg font-semibold text-slate-800">Edit Steps</h3>
                                <p class="text-sm text-slate-400">Modify individual execution steps</p>
                            </div>
                        </div>
                        <button 
                            class="p-2 rounded-xl hover:bg-slate-100 transition-colors"
                            @click="showStepsEditor = false"
                        >
                            <Icon icon="solar:close-circle-bold-duotone" class="text-2xl text-slate-400 hover:text-slate-600"/>
                        </button>
                    </div>
                    <!-- Content -->
                    <div class="flex-1 p-6 overflow-auto space-y-4">
                        <!-- Empty state -->
                        <div v-if="stepsContent.length === 0" class="flex flex-col items-center justify-center py-12 text-slate-400">
                            <Icon icon="solar:document-text-bold-duotone" class="text-5xl mb-3 opacity-50" />
                            <p class="text-sm">No editable steps available</p>
                        </div>
                        <!-- Steps list -->
                        <div v-else v-for="(item, index) in stepsContent" :key="index" class="space-y-2">
                            <div class="flex items-center justify-between">
                                <label class="text-sm font-medium text-slate-600">Step {{ item.stepNumber || index + 1 }}</label>
                                <span v-if="item.content !== item.backup" class="text-xs text-amber-500 bg-amber-50 px-2 py-0.5 rounded-full">Modified</span>
                            </div>
                            <textarea 
                                v-model="item.content" 
                                class="w-full h-40 p-4 bg-slate-900 text-slate-100 rounded-xl border border-slate-700 focus:border-primary-400 focus:ring-2 focus:ring-primary-500/20 resize-none font-mono text-sm transition-all"
                                placeholder="Enter shell script..."
                            ></textarea>
                        </div>
                </div>
                    <!-- Footer -->
                    <div class="flex justify-end gap-3 px-6 py-4 border-t border-slate-100 bg-slate-50/50">
                        <button 
                            class="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 transition-colors"
                            @click="showStepsEditor = false"
                        >
                            Cancel
                        </button>
                        <button 
                            class="px-6 py-2 rounded-xl bg-white border border-amber-300 text-amber-600 font-medium hover:bg-amber-50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                            :disabled="stepsContent.length === 0"
                            @click="saveSteps"
                        >
                            Save Only
                        </button>
                        <button 
                            class="px-6 py-2 rounded-xl bg-gradient-to-r from-emerald-500 to-cyan-500 text-white font-medium hover:shadow-lg hover:shadow-emerald-500/30 transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                            :disabled="stepsContent.length === 0"
                            @click="saveAndResume"
                        >
                            <Icon icon="solar:play-bold" class="text-lg" />
                            Save & Resume
                        </button>
                </div>
                </div>
            </div>
        </Transition>
    </Teleport>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import Avatar from './Avatar.vue'
import Text from './Text.vue'
import { Icon } from '@iconify/vue';
import { useMessage } from 'naive-ui';
import usePageStore from "@/store/pageStore";

const props = defineProps({
    text: {
        type: String,
        default: "Default message"
    },
    inversion: {
        type: Boolean,
        default: false
    },
    generate: {
        type: Boolean,
        default: false
    },
    index: {
        type: Number,
        default: 0
    },
    total: {
        type: Number,
        default: 0
    },
    type: {
        type: String,
        default: "text"
    }
})
const asRawText = ref(props.inversion);
const $emits = defineEmits(['stop', 'update-plan'])
const showPlanEditor = ref(false);
const tempPlan = ref("")
const pageStore = usePageStore();
const message = useMessage();
const isStopping = ref(false);

const canStop = computed(() => {
    const length = pageStore.current_session.execute_info.length - 1;
    return length > 0 && pageStore.current_session.execute_info[length].type == "execute";
})

async function handleStop() {
    if (isStopping.value) return;
    
    isStopping.value = true;
    try {
        $emits('stop');
        await pageStore.stopCurrentExecutePlan(false);
        message.success("Stop request sent");
    } catch (error) {
        console.error("Error stopping execution:", error);
        message.error("Failed to stop execution");
    } finally {
        // Wait a moment before resetting state so user sees Stopping... feedback
        setTimeout(() => {
            isStopping.value = false;
        }, 1500);
    }
}

const showStepsEditor = ref(false);
const stepsContent = ref<any>([])

function openPlanEditor() {
    showPlanEditor.value = true;
    tempPlan.value = pageStore.current_session.execute_info[pageStore.current_session.execute_info.length - 1].prevText as string;
}

async function executePlan() {
    pageStore.addCurrentExecuteInfo("computer", "Starting The Task...", true, "thinking");
    await pageStore.executePlan();
    await pageStore.getCurrentExecuteInfo();
    message.success("Execute Success");
    $emits('update-plan', true);
}

async function savePlan() {
    try {
        const final_data = JSON.parse(tempPlan.value);
        await pageStore.updateCurrentPlan(final_data['plan']);
        await pageStore.getCurrentExecuteInfo();
        showPlanEditor.value = false;
        message.success("Update Success");
        $emits('update-plan');
    }
    catch (e) {
        message.error("JSON Error");
    }
}

function openStepsEditor() {
    showStepsEditor.value = true;
    stepsContent.value = [];
    
    // Find entries containing steps in execute_info (from end to start)
    const executeInfos = pageStore.current_session.execute_info;
    let foundSteps: any[] = [];
    
    for (let i = executeInfos.length - 1; i >= 0; i--) {
        const info = executeInfos[i];
        if (info.steps && Array.isArray(info.steps) && info.steps.length > 0) {
            foundSteps = info.steps;
            break;
        }
    }
    
    // Parse step data
    if (foundSteps.length > 0) {
        for (let i = 0; i < foundSteps.length; i++) {
            const step = foundSteps[i];
            // Support multiple data formats
            const shellContent = step.shell || step.script || step.command || step.content || "";
            const stepNum = step.step_number || step.stepNumber || step.number || (i + 1);
            
            if (shellContent) {
                stepsContent.value.push({
                    content: shellContent,
                    backup: shellContent,
                    stepNumber: stepNum,
                })
            }
        }
    }
    
    // If no steps found, show hint
    if (stepsContent.value.length === 0) {
        message.warning("No editable steps found");
    }
}

async function saveSteps() {
    try {
        for await (const step of stepsContent.value) {
            if (step.content != step.backup) {
                await pageStore.updateCurrentExecuteStep(step.stepNumber, step.content);
            }
        }
        await pageStore.getCurrentExecuteInfo();
        showStepsEditor.value = false;
        message.success("Update Success");
        $emits('update-plan');
    }
    catch (e) {
        message.error("Update Error");
    }
}

async function saveAndResume() {
    try {
        // Save changes first
        for await (const step of stepsContent.value) {
            if (step.content != step.backup) {
                await pageStore.updateCurrentExecuteStep(step.stepNumber, step.content);
            }
        }
        showStepsEditor.value = false;
        message.success("Steps Updated");
        
        // Then resume execution
        pageStore.addCurrentExecuteInfo("computer", "Resuming execution...", true, "thinking");
        await pageStore.executePlan();
        await pageStore.getCurrentExecuteInfo();
        message.success("Execution Resumed");
        $emits('update-plan', true);
    }
    catch (e) {
        message.error("Error: " + e);
    }
}

async function onGenerateReport() {
    pageStore.addCurrentExecuteInfo("computer", "Generate Report...", true, 'thinking');
    await pageStore.generateReport();
    await pageStore.getCurrentExecuteInfo();
    message.success("Generate Success");
    $emits('update-plan');
}
</script>

<style scoped lang="scss">
/* Message slide-in animation */
.animate-slide-up {
    animation: slideUp 0.4s ease-out forwards;
}

@keyframes slideUp {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

/* Modal scale animation */
.animate-scale-in {
    animation: scaleIn 0.3s ease-out forwards;
}

@keyframes scaleIn {
    from { opacity: 0; transform: scale(0.95); }
    to { opacity: 1; transform: scale(1); }
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
    transform: scale(0.95);
}
</style>
