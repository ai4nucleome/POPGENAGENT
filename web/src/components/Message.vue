<template>
    <div 
        ref="messageRef" 
        class="flex w-full mb-6 overflow-hidden animate-slide-up" 
        :class="[{ 'flex-row-reverse': props.inversion }]"
        :style="{ animationDelay: '0.1s' }"
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
            <!-- Message bubble -->
            <div class="flex items-end gap-2" :class="[inversion ? 'flex-row-reverse' : 'flex-row']">
                <div class="relative group">
                    <!-- Message glow effect (user messages only) -->
                    <div 
                        v-if="inversion" 
                        class="absolute -inset-1 bg-gradient-to-r from-primary-500/20 to-accent-500/20 rounded-2xl blur opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                    ></div>
                    <Text 
                        ref="textRef" 
                        :inversion="inversion" 
                        :text="text" 
                        :as-raw-text="asRawText" 
                        :generate="generate"
                    />
                </div>
            </div>
            
            <!-- Stop generating button -->
            <div 
                v-if="generate" 
                class="mt-3 animate-fade-in"
            >
                <button 
                    class="group inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-rose-50 hover:bg-rose-100 border border-rose-200 transition-all duration-200 hover:scale-[1.02] active:scale-[0.98]"
                    @click="$emit('stop')"
                >
                    <div class="w-4 h-4 rounded-full border-2 border-rose-400 flex items-center justify-center">
                        <div class="w-1.5 h-1.5 rounded-sm bg-rose-500"></div>
                    </div>
                    <span class="text-sm font-medium text-rose-600">Stop Generating</span>
                </button>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import Avatar from './Avatar.vue'
import Text from './Text.vue'

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
    }
})
const asRawText = ref(props.inversion);

const $emits = defineEmits(['stop'])
</script>

<style scoped lang="scss">
/* Message slide-in animation */
@keyframes slide-up {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.animate-slide-up {
    animation: slide-up 0.4s ease-out forwards;
}

/* Fade-in animation */
@keyframes fade-in {
    from { opacity: 0; }
    to { opacity: 1; }
}

.animate-fade-in {
    animation: fade-in 0.3s ease-out;
}
</style>
