<template>
    <div class="flex flex-col h-full overflow-hidden">
        <div class="font-bold text-sm mb-3">KNOWLEDGE BASE</div>
        <div class="flex-1 overflow-hidden">
            <NScrollbar class="py-2">
                <div class="flex flex-col gap-2 text-sm px-1">
                    <template v-if="knowledgeItems.length === 0">
                        <div class="flex flex-col items-center mt-4 text-center text-neutral-300">
                            <Icon icon="ri:inbox-line" class="mb-2 text-3xl" />
                            <span>No knowledge entries</span>
                        </div>
                    </template>
                    <template v-else>
                        <div 
                            v-for="(item, index) in knowledgeItems" 
                            :key="item.id"
                            class="p-4 border rounded-xl bg-slate-50 hover:bg-white transition-colors"
                        >
                            <div class="flex items-start justify-between gap-3">
                                <div class="flex-1 min-w-0">
                                    <div class="flex items-center gap-2 mb-2">
                                        <span class="px-2 py-0.5 text-xs font-medium rounded-full bg-primary-100 text-primary-600">
                                            {{ item.source }}
                                        </span>
                                    </div>
                                    <div 
                                        class="text-sm text-slate-600 line-clamp-3 cursor-pointer hover:text-slate-800"
                                        @click="viewItem(item)"
                                    >
                                        {{ item.content_preview }}
                                    </div>
                                </div>
                                <button 
                                    class="flex items-center gap-1 text-xs text-slate-400 hover:text-red-500 transition-colors shrink-0"
                                    @click="confirmDelete(item)"
                                >
                                    <Icon icon="ri:delete-bin-line" class="text-sm"/>
                                    <span>DELETE</span>
                                </button>
                            </div>
                        </div>
                    </template>
                </div>
            </NScrollbar>
        </div>
        
        <div class="font-bold text-sm mt-4 mb-2">ADD NEW KNOWLEDGE</div>
        <!-- Add new knowledge entry -->
        <div class="space-y-3">
            <div>
                <label class="text-xs text-slate-500 mb-1 block">Source Name</label>
                <NInput v-model:value="newSource" placeholder="e.g., PLINK, smartPCA, custom" size="small" />
            </div>
            <div>
                <label class="text-xs text-slate-500 mb-1 block">Content</label>
                <NInput 
                    v-model:value="newContent" 
                    type="textarea" 
                    placeholder="Enter knowledge content here..."
                    :rows="4"
                />
            </div>
            <NButton 
                type="primary" 
                class="w-full"
                :disabled="!newContent.trim()"
                @click="addKnowledge"
            >
                <template #icon>
                    <Icon icon="ri:add-line" />
                </template>
                Add Knowledge Entry
            </NButton>
        </div>
        
        <!-- Delete confirmation dialog -->
        <Alert v-model:show="showAlert" @submit="onDeleteItem" />
        
        <!-- View detail dialog -->
        <NModal v-model:show="showDetail" preset="card" style="width: 600px; max-width: 90vw;" title="Knowledge Detail">
            <div v-if="selectedItem" class="space-y-3">
                <div class="flex items-center gap-2">
                    <span class="px-2 py-0.5 text-xs font-medium rounded-full bg-primary-100 text-primary-600">
                        {{ selectedItem.source }}
                    </span>
                </div>
                <div class="p-4 bg-slate-50 rounded-xl text-sm text-slate-700 whitespace-pre-wrap max-h-[400px] overflow-auto">
                    {{ selectedItem.content }}
                </div>
            </div>
        </NModal>
    </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { Icon } from '@iconify/vue';
import { NScrollbar, NInput, NButton, NModal, useMessage } from "naive-ui";
import usePageStore from "@/store/pageStore";
import Alert from '@/components/Alert.vue';

interface KnowledgeItem {
    id: string;
    source: string;
    content_preview: string;
    content: string;
}

const pageStore = usePageStore();
const message = useMessage();

const knowledgeItems = ref<KnowledgeItem[]>([]);
const newSource = ref('custom');
const newContent = ref('');
const showAlert = ref(false);
const showDetail = ref(false);
const selectedItem = ref<KnowledgeItem | null>(null);
let itemToDelete: KnowledgeItem | null = null;

onMounted(async () => {
    await loadKnowledgeItems();
});

async function loadKnowledgeItems() {
    try {
        await pageStore.getToolFiles(true);
        knowledgeItems.value = pageStore.settings.tools as unknown as KnowledgeItem[];
    } catch (error) {
        message.error('Failed to load knowledge items');
    }
}

function viewItem(item: KnowledgeItem) {
    selectedItem.value = item;
    showDetail.value = true;
}

function confirmDelete(item: KnowledgeItem) {
    itemToDelete = item;
    showAlert.value = true;
}

async function onDeleteItem() {
    if (!itemToDelete) return;
    
    try {
        const result = await pageStore.deleteToolFile(itemToDelete.id);
        if (result) {
            message.success('Knowledge entry deleted');
            await loadKnowledgeItems();
        } else {
            message.error('Delete failed');
        }
    } catch (error) {
        message.error('Delete error');
    }
    itemToDelete = null;
}

async function addKnowledge() {
    if (!newContent.value.trim()) {
        message.warning('Please enter content');
        return;
    }
    
    try {
        await pageStore.addKnowledgeEntry(newContent.value, newSource.value || 'custom');
        message.success('Knowledge entry added');
        newContent.value = '';
        newSource.value = 'custom';
        await loadKnowledgeItems();
    } catch (error) {
        message.error('Failed to add knowledge entry');
    }
}
</script>

<style scoped lang="scss">
.line-clamp-3 {
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
</style>
