<template>
    <div>
        <div class=" font-bold text-sm">EXECUTE OR NOT</div>
        <div class="flex items-center justify-between px-2 py-1 my-4 bg-white rounded">
            <n-switch v-model:value="pageStore.settings.executor" :rail-style="railStyle" size="large" @update:value="onUpdate">
                <template #checked>
                    True
                </template>
                <template #unchecked>
                    False
                </template>
            </n-switch>
        </div>
    </div>
</template>
<script setup lang="ts">
import { NSwitch } from 'naive-ui';
import type { CSSProperties } from 'vue'
import usePageStore from "@/store/pageStore"
import { useMessage } from 'naive-ui';

const pageStore = usePageStore();
const message = useMessage();
const railStyle = ({focused,checked}: {focused: boolean, checked: boolean}) => {
    const style: CSSProperties = {}
    if (checked) {
        style.background = '#2080f0'
        if (focused) {
            style.boxShadow = '0 0 0 2px #d0305040'
        }
    }
    else {
        style.background = '#d03050'
        style.color = '#000000'
        if (focused) {
            style.boxShadow = '0 0 0 2px #2080f040'
        }
    }
    return style
}

async function onUpdate(){
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
}

</script>
<style scoped lang="scss">

</style>