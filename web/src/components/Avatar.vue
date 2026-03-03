<template>
    <!-- AI avatar -->
    <div v-if="props.isUser" class="relative group">
        <!-- Glow effect -->
        <div class="absolute -inset-1 bg-gradient-to-br from-primary-500/30 to-accent-500/30 rounded-xl blur opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
        <!-- Avatar container -->
        <div class="relative w-10 h-10 rounded-xl bg-gradient-to-br from-primary-50 to-accent-50 flex items-center justify-center shadow-soft border border-white/50">
            <img :src="computerAvatar" class="w-6 h-6" alt="AI">
        </div>
    </div>
    
    <!-- User avatar -->
    <div v-else class="relative group">
        <!-- Glow effect -->
        <div class="absolute -inset-1 bg-gradient-to-br from-primary-500/30 to-accent-500/30 rounded-xl blur opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
        <!-- Avatar -->
        <img 
            :src="defaultAvatar" 
            class="relative w-10 h-10 rounded-xl object-cover ring-2 ring-white shadow-soft"
            alt="User"
        />
    </div>
</template>

<script setup lang="ts">
const computerAvatar = new URL("../assets/icon.svg", import.meta.url).href;
const defaultAvatar = new URL("../assets/avatar.jpg", import.meta.url).href;
const props = defineProps(['isUser'])
</script>

<style scoped lang="scss">
</style>
