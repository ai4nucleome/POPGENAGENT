<template>
    <div class="flex flex-col h-full overflow-hidden">
        <div class=" font-bold text-sm">MANAGE DOCS</div>
        <n-button type="info" class="w-40 my-2" @click="showModal=true">NEW DOCUMENT</n-button>
        <div class="h-full overflow-hidden">
            <NScrollbar class="py-2">
                <div class="flex flex-col gap-2 text-sm px-1">
                    <template v-if="pageStore.settings.docs.length==0">
                        <div class="flex flex-col items-center mt-4 text-center text-neutral-300">
                            <Icon icon="ri:inbox-line" class="mb-2 text-3xl " />
                            <span>Empty</span>
                        </div>
                    </template>
                    <template v-else>
                        <div class="p-4 border box-border flex flex-col rounded-lg bg-[#f1f3f9]" v-for="(contents, page) in pageStore.settings.docCompute" :key="page">
                            <div class="flex items-center">
                                <div class="text-base">{{ page }}</div>
                                
                            </div>
                            <div v-for="(content) in contents" :key="content" class="mb-4">
                                <div class=" text-gray-500 cursor-pointer hover:text-[#437BFD] flex items-center gap-1 justify-end"
                                    @click=" showAlert = true; pageContent.page=page;pageContent.content=content; ">
                                    <Icon icon="ri:delete-bin-line" class="text-xs"/>
                                    <span>DELETE</span>
                                </div>
                                <!-- <pre class=" whitespace-break-spaces break-all my-2">{{ doc.content }}</pre> -->
                                <n-ellipsis expand-trigger="click" line-clamp="4" :tooltip="false">{{ content }}</n-ellipsis>
                            </div>
                        </div>
                    </template>
                </div>
            </NScrollbar>
        </div>
        <n-modal v-model:show="showModal">
            <div class="p-8 w-[600px] rounded-lg bg-white">
                <div>
                    <Icon icon="iconamoon:close-thin" class="text-gray-500 text-3xl absolute top-2 right-2 cursor-pointer hover:text-[#437BFD]"
                            @click="showModal=false"></Icon>
                </div>
                <div>
                    <div  class="flex items-center justify-between px-2 py-1 my-4 bg-white rounded border">
                        <n-input
                            type="textarea"
                            placeholder="Input Content"
                            v-model:value="docInfo"
                        />
                    </div>
                    <div class="flex items-center justify-between px-2 py-1 my-4 bg-white rounded border">
                        <n-input-number class="w-full" v-model:value="docOrder"/>
                    </div>
                </div>
                <div>
                    <n-button type="info" class="w-20" @click="onAddDocFile">OK</n-button>
                    <n-button class="w-20 ml-4" @click="showModal=false">Cancel</n-button>
                </div>
            </div>
        </n-modal>
        <Alert v-model:show="showAlert" @submit="onDeleteDocFile" />
    </div>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { Icon } from '@iconify/vue';
import { NScrollbar, NButton, NModal, NInput, NInputNumber, NEllipsis, useMessage } from "naive-ui";
import usePageStore from "@/store/pageStore"
import Alert from '../../components/Alert.vue'

const showModal = ref(false)
const docInfo = ref("")
const docOrder = ref(1)
const message = useMessage()
const pageStore = usePageStore();
const showAlert = ref(false);
let pageContent:{
    page: string|number,
    content: string
} = {
    page: -1,
    content: ""
};

onMounted(()=>{
    pageStore.getDocFiles();
})

async function onDeleteDocFile(){
    try {
        const result = await pageStore.deleteDocFile(pageContent);
        if(result){
            if(result.status && result.status=="success"){
                message.success("Delete Success")
            }else{
                message.error("Delete Error")
            }
        }
    } catch (error) {
        message.error("API Error")
    }
}

async function onAddDocFile(){
    if(!docOrder.value && docOrder.value!=0){
        message.error("input a number!")
        return;
    }
    if(!docInfo.value){
        message.error("input the doc content!")
        return;
    }
    try {
        const result = await pageStore.addDocFile({ page:docOrder.value, content:docInfo.value });
        if(result){
            if(result.status && result.status=="success"){
                message.success("Add Success")
            }else{
                message.error("Add Error")
            }
        }
    } catch (error) {
        message.error("API Error")
    }
    showModal.value = false;
    docInfo.value = "";
}
</script>
<style scoped lang="scss">

</style>