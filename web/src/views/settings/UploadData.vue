<template>
    <div>
        <div class=" font-bold text-sm">UPLOAD GOOGLE DRIVE FILE</div>
        <div class="flex items-center justify-between px-2 py-1 my-4 bg-white rounded border">
            <n-input v-model:value="inputValue" type="text" placeholder="Enter Google Drive link" clearable />
        </div>
        <n-button type="info" class="w-20" @click="uploadToGoogle">OK</n-button>
        <n-button class="w-20 ml-4" @click="pageStore.settings.show=false">Cancel</n-button>
    </div>
</template>
<script setup lang="ts">
import { ref } from 'vue';
import { NInput, NButton } from 'naive-ui';
import { useMessage } from 'naive-ui'
import usePageStore from "@/store/pageStore"

const pageStore = usePageStore();
const message = useMessage();
const inputValue = ref("");

async function uploadToGoogle(){
    if(!inputValue.value){
        message.error("input the url");
        return;
    }
    try {
        await pageStore.uploadToGoogleDrive(inputValue.value);
        message.success("Upload Success");
    } catch (error:any) {
        console.log(error);
        const text = error.response.data.message;
        message.error(text);
    }
}

</script>
<style scoped lang="scss">

</style>