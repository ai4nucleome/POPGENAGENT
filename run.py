from core.GenAgent import GenAgent
from config_loader import get_llm_config

if __name__ == "__main__":
    cfg = get_llm_config()
    api_key = cfg["api_key"]
    base_url = cfg["base_url"]

    manager = GenAgent(api_key, base_url, excutor=True, tools_dir="tools", id='95')

    datalist = [
        "./data/1000GP_pruned.bed: SNP file in bed format",
        "./data/1000GP_pruned.bim: snp info associate with the bed format",
        "./data/1000GP_pruned.fam: data information, the first col is population, the second is sample ID",
    ]
    goal = 'please help me to perform Complete population genetic analysis including all advanced analyses'

    manager.execute_PLAN(goal, datalist)
    print("**********************************************************")

    PLAN_results_dict = manager.execute_TASK(datalist)
    print(PLAN_results_dict)
