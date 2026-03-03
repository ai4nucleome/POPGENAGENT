<template>
    <button 
        class="group relative flex items-center justify-center w-12 h-12 rounded-xl transition-all duration-300"
        :class="[
            disabled 
                ? 'cursor-not-allowed bg-slate-100' 
                : 'cursor-pointer bg-gradient-to-br from-primary-500 to-accent-500 hover:shadow-lg hover:shadow-primary-500/30 hover:scale-105 active:scale-95'
        ]"
        @click="onClick"
    >
        <!-- Background glow -->
        <div 
            v-if="!disabled"
            class="absolute inset-0 bg-gradient-to-br from-primary-400 to-accent-400 rounded-xl blur-lg opacity-0 group-hover:opacity-50 transition-opacity duration-300"
        ></div>
        
        <!-- Icon -->
        <div class="relative">
            <!-- Send icon -->
            <svg 
                class="w-5 h-5 transition-all duration-300"
                :class="disabled ? 'text-slate-400' : 'text-white group-hover:translate-x-0.5 group-hover:-translate-y-0.5'"
                viewBox="0 0 24 24" 
                fill="currentColor"
            >
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
        </svg>
    </div>
        
        <!-- Pulse effect -->
        <div 
            v-if="!disabled"
            class="absolute inset-0 rounded-xl animate-ping bg-primary-500/20 group-hover:animation-running"
            style="animation-duration: 2s;"
        ></div>
    </button>
</template>

<script setup lang="ts">
const $emits = defineEmits(['send'])
const props = defineProps({
    disabled: {
        type: Boolean,
        default: false
    }
})

function onClick() {
    if (!props.disabled) $emits("send");
}
</script>

<style scoped lang="scss">
/* Pulse animation optimization */
button:not(:hover) .animate-ping {
    animation-play-state: paused;
}

button:hover .animate-ping {
    animation-play-state: running;
}
</style>
