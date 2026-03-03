<template>
    <n-modal v-model:show="isVisible">
        <div class="relative p-6 w-[420px] rounded-2xl bg-white shadow-2xl">
            <!-- Close button -->
            <button 
                class="absolute top-4 right-4 p-1.5 rounded-xl hover:bg-slate-100 transition-colors"
                @click="closeModal"
            >
                <Icon icon="solar:close-circle-bold-duotone" class="text-xl text-slate-400 hover:text-slate-600"/>
            </button>
            
            <!-- Icon -->
            <div class="flex justify-center mb-4">
                <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-rose-100 to-orange-100 flex items-center justify-center">
                    <Icon icon="solar:danger-triangle-bold-duotone" class="text-3xl text-rose-500"/>
                </div>
            </div>
            
            <!-- Content -->
            <div class="text-center mb-6">
                <h3 class="text-xl font-bold text-slate-800 mb-2">{{ title }}</h3>
                <p class="text-slate-500">{{ message }}</p>
            </div>
            
            <!-- Buttons -->
            <div class="flex gap-3">
                <button 
                    class="flex-1 px-4 py-3 rounded-xl border border-slate-200 text-slate-600 font-medium hover:bg-slate-50 transition-colors"
                    @click="closeModal"
                >
                    Cancel
                </button>
                <button 
                    class="flex-1 px-4 py-3 rounded-xl bg-gradient-to-r from-rose-500 to-orange-500 text-white font-medium hover:shadow-lg hover:shadow-rose-500/30 transition-all"
                    @click="onSubmit"
                >
                    Delete
                </button>
            </div>
        </div>
    </n-modal>
</template>
  
<script setup lang="ts">
import { ref, watch } from 'vue';
import { NModal } from "naive-ui";
import { Icon } from '@iconify/vue';
  
const props = defineProps({
    show: {
        type: Boolean,
        default: false
    },
    title: {
        type: String,
        default: 'Delete Project'
    },
    message: {
        type: String,
        default: 'Are you sure you want to delete this project? This action cannot be undone.'
    }
});
  
const emit = defineEmits(['update:show', 'submit']);
  
const isVisible = ref(props.show);
  
watch(
    () => props.show,
    (newValue) => {
      isVisible.value = newValue;
    }
);
  
watch(
    isVisible,
    (newValue) => {
        emit('update:show', newValue);
    }
);
  
const closeModal = () => {
    isVisible.value = false;
};
  
const onSubmit = () => {
    emit('submit');
    closeModal();
};
</script>
  
<style scoped lang="scss">
</style>  
