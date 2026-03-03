<template>
    <div class=" fixed left-0 top-0 inset-0 bg-slate-800/80 z-10">
        <div class="absolute inset-0" @click="onCloseFiles"></div>
        <div class="absolute w-[80%] min-w-[600px] h-[80%] min-h-[360px] bg-white rounded-lg flex overflow-hidden left-[50%] top-[50%] translate-x-[-50%] translate-y-[-50%]">
            <div class="relative flex-1 px-4 py-6 w-[400px]" ref="tableContainer">
                <div class=" flex justify-end">
                    <Icon icon="iconamoon:close-thin" class="text-gray-500 text-3xl cursor-pointer hover:text-[#437BFD]"
                        @click="onCloseFiles"></Icon>
                </div>
                <n-config-provider :theme-overrides="themeOverrides">
                    <n-data-table :columns="columns" :data="createData" bordered striped bottom-bordered
                        :row-key="rowKey"
                        :checked-row-keys="pageStore.analysis_files.selects"
                        @update:checked-row-keys="handleCheck"
                        :max-height="maxHeight"
                        :single-line="false"
                    ></n-data-table>
                </n-config-provider>
                <div class=" flex justify-end">
                    <n-button type="info" class=" mt-4" @click="pageStore.analysis_files.show=false;">OK</n-button>
                </div>
            </div>
        </div>
    </div>
    <Teleport to="body">
        <div v-if="showEdit" class=" fixed w-full h-full z-20 bg-slate-800/80 left-0 top-0">
            <div class="absolute w-[500px] bg-white rounded-lg flex overflow-hidden left-[50%] top-[50%] translate-x-[-50%] translate-y-[-50%]">
                <div class="relative flex-1 px-4 py-6">
                    <div class=" flex justify-end">
                        <Icon icon="iconamoon:close-thin" class="text-gray-500 text-3xl cursor-pointer hover:text-[#437BFD]"
                            @click="showEdit=false"></Icon>
                    </div>
                    <n-input
                        v-model:value="newDescription"
                        type="textarea"
                        placeholder="fill in description"
                    />
                    <div class=" flex justify-end">
                        <n-button type="info" class=" mt-4" @click="onSaveDescription">OK</n-button>
                    </div>
                </div>
            </div>
        </div>
    </Teleport>
</template>
<script setup lang="ts">
import usePageStore from "@/store/pageStore";
import type { DataTableColumns, DataTableRowKey } from 'naive-ui'
import { Icon } from '@iconify/vue';
import { NDataTable, NButton, NConfigProvider, GlobalThemeOverrides, NInput, useMessage } from 'naive-ui';
import { computed, onMounted, h, ref, onUnmounted } from "vue";

interface DataRow{
    id: number;
    filename: string;
    description: string;
}

const pageStore = usePageStore();
function createColumns({ edit }: { edit: (row: DataRow) => void }): DataTableColumns<DataRow> {
    return [
        {
            type: 'selection'
        },
        {
            title: "ID",
            key: "id",
            width: 80,
            align: "center"
        },
        {
            title: "Filename",
            key: "filename",
            width: 300,
            ellipsis: true
        },
        {
            title: "Description",
            key: "description",
            ellipsis: true
        },
        {
        title: "Action",
        key: "actions",
        width: 80,
        render(row) {
            return h(
            NButton,
            {
                strong: true,
                tertiary: true,
                size: "small",
                onClick: () => edit(row)
            },
            { default: () => "Edit" }
            );
        }
        }
    ]
}
const columns = createColumns({
        edit(row: DataRow) {
            console.log(row);
            currentFileInfo = row;
            showEdit.value = true;
            newDescription.value = row.description;
        }
    })
const createData = computed(()=>{
    const cs:DataRow[] = [];
    for (let i = 0; i < pageStore.analysis_files.files.length; i++) {
        cs.push({
            id: pageStore.analysis_files.files[i].id,
            filename: pageStore.analysis_files.files[i].filename,
            description: pageStore.analysis_files.files[i].description
        })
    }
    return cs;
})
const rowKey = (row: DataRow) => row.id;
const themeOverrides: GlobalThemeOverrides = {
    common: {
        primaryColor: '#437BFD'
    }
}
const tableContainer = ref<HTMLElement>();
const tableContainerHeight = ref(100);
const maxHeight = computed(()=>{
    if(tableContainer.value){
        return tableContainerHeight.value - 180;
    }
    return 300;
})
const showEdit = ref(false);
const newDescription = ref("");
let currentFileInfo:DataRow;
const message = useMessage();

onMounted(()=>{
    pageStore.getAnalysisFiles();
    window.addEventListener("resize", onResize);
    onResize();
})

onUnmounted(()=>{
    window.removeEventListener("resize", onResize);
})

function onCloseFiles(){
    pageStore.analysis_files.show=false;
    // pageStore.analysis_files.selects = [];
}

function handleCheck(rowKeys: DataTableRowKey[]) {
    pageStore.analysis_files.selects = rowKeys as number[];
}

function onResize(){
    tableContainerHeight.value = tableContainer.value!.getBoundingClientRect().height;
}

function onSaveDescription(){
    showEdit.value = false;
    if(newDescription.value != currentFileInfo.description){
        pageStore.updateAnalysisFileDescription(currentFileInfo.id, currentFileInfo.filename, newDescription.value);
        message.success("update success");
    }
}

</script>
<style scoped lang="scss">

</style>