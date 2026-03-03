<template>
    <div>
        <div class=" font-bold text-sm">API SETTING</div>
        <div class="flex items-center justify-between px-2 py-1 my-4 bg-white rounded border">
            <n-input v-model:value="pageStore.settings.api_key" type="text" placeholder="Enter value here" clearable />
        </div>
        <n-button type="info" class="w-20" @click="onUpdate" :disabled="disabledButton">OK</n-button>
        <n-button class="w-20 ml-4" @click="pageStore.settings.show=false">Cancel</n-button>
    </div>
</template>
<script setup lang="ts">
import { NInput, NButton } from 'naive-ui';
import usePageStore from "@/store/pageStore"
import { useMessage } from 'naive-ui'
import { ref } from 'vue';

const pageStore = usePageStore();
const message = useMessage();
const disabledButton = ref(false);

async function onUpdate(){
    disabledButton.value = true;
    try {
        const result = await pageStore.updateSettings();
        if(result.status && result.status=="success"){
            message.success("Update Success")
        }else{
            message.error("Update Error")
        }
    } catch (error) {
        message.success("update_settings api error")
    }
    disabledButton.value = false;
}
</script>
<style scoped lang="scss">

</style>