import { ref, inject, provide } from "vue";

export const I18N_KEY = Symbol("i18n");

const messages = {
  "zh-CN": {
    nav: {
      overview: "概览",
      chat: "对话",
      data: "数据",
      settings: "设置",
    },
    brand: {
      title: "Omics Copilot",
      subtitle: "AI 驱动的多组学分析",
    },
    theme: {
      light: "浅色",
      dark: "深色",
    },
    lang: {
      zh: "中",
      en: "EN",
    },
    overview: {
      title: "Omics Copilot",
      subtitle: "AI 驱动的多组学分析平台",
      quickStart: "快速开始",
      stats: {
        files: "数据文件",
        analyses: "分析任务",
        gpu: "GPU 状态",
      },
      steps: {
        upload: {
          title: "上传数据",
          desc: "上传 .h5ad、.csv、.fastq 等多组学数据文件",
        },
        ask: {
          title: "提出问题",
          desc: "用自然语言描述你的分析需求，AI 自动规划分析流程",
        },
        explore: {
          title: "探索结果",
          desc: "交互式查看分析结果和可视化图表",
        },
      },
      gpu: {
        title: "GPU 状态",
        available: "可用",
        unavailable: "不可用",
      },
    },
    chat: {
      title: "对话分析",
      subtitle: "用自然语言与 AI 协作进行多组学分析",
      placeholder: "描述你的分析需求...",
      send: "发送",
      stop: "停止",
      emptyTitle: "开始你的组学分析之旅",
      emptyDesc: "输入分析需求，或从下方示例中选择以开始",
      typing: "思考中...",
      modality: {
        auto: "自动",
        scrna: "单细胞",
        bulk: "Bulk RNA",
        spatial: "空间组学",
        tcr: "免疫组库",
        metagenomics: "宏基因组",
        amplicon: "扩增子",
      },
      examples: [
        "对这个 scRNA-seq 数据进行 QC 和聚类分析",
        "找出 marker genes 并进行差异分析",
        "查看 GPU 是否可用",
        "做 Bulk RNA-seq 差异表达和富集分析",
      ],
      plan: {
        title: "分析计划",
      },
      tool: {
        running: "执行中",
        success: "完成",
        error: "失败",
      },
    },
    data: {
      title: "数据管理",
      subtitle: "管理多组学数据文件",
      upload: "上传文件",
      filterAll: "全部",
      filterH5ad: ".h5ad",
      filterCsv: ".csv/.tsv",
      filterOther: "其他",
      empty: "暂无数据文件",
      emptyHint: "上传 .h5ad, .h5mu, .csv, .tsv, .fastq 等文件",
      delete: "删除",
      info: {
        title: "文件信息",
        name: "文件名",
        size: "大小",
        type: "类型",
        created: "创建时间",
        shape: "形状",
      },
    },
    file: {
      upload: "选择或拖拽文件到此处",
      uploading: "上传中...",
      invalidType: "不支持的文件类型",
      dropHere: "释放以上传文件",
    },
    settings: {
      title: "LLM 设置",
      subtitle: "配置大语言模型 API 连接",
      addProvider: "添加提供商",
      noProviders: "尚未配置 LLM 提供商",
      noProvidersHint: "点击上方按钮添加 OpenAI、DeepSeek 或其他兼容的 API",
      apiKey: "API Key",
      baseUrl: "Base URL",
      model: "模型",
      name: "名称",
      namePlaceholder: "自定义名称",
      setActive: "设为活跃",
      active: "当前使用",
      save: "保存配置",
      connected: "已连接",
      notConnected: "未连接",
      edit: "编辑",
      testConnection: "测试连接",
      testing: "测试中...",
      testSuccess: "连接成功！",
      testFailed: "连接失败",
      saveSuccess: "配置已保存",
      saveFailed: "保存失败",
    },
    status: {
      loading: "加载中...",
      error: "出错了",
      retry: "重试",
      success: "成功",
      noData: "暂无数据",
    },
  },

  "en-US": {
    nav: {
      overview: "Overview",
      chat: "Chat",
      data: "Data",
      settings: "Settings",
    },
    brand: {
      title: "Omics Copilot",
      subtitle: "AI-Powered Multi-Omics Analysis",
    },
    theme: {
      light: "Light",
      dark: "Dark",
    },
    lang: {
      zh: "中",
      en: "EN",
    },
    overview: {
      title: "Omics Copilot",
      subtitle: "AI-Powered Multi-Omics Analysis Platform",
      quickStart: "Quick Start",
      stats: {
        files: "Data Files",
        analyses: "Analyses",
        gpu: "GPU Status",
      },
      steps: {
        upload: {
          title: "Upload Data",
          desc: "Upload .h5ad, .csv, .fastq and other omics data files",
        },
        ask: {
          title: "Ask Questions",
          desc: "Describe your analysis needs in natural language, AI plans the workflow",
        },
        explore: {
          title: "Explore Results",
          desc: "Interactively explore analysis results and visualizations",
        },
      },
      gpu: {
        title: "GPU Status",
        available: "Available",
        unavailable: "Unavailable",
      },
    },
    chat: {
      title: "Chat Analysis",
      subtitle: "Collaborate with AI for multi-omics analysis using natural language",
      placeholder: "Describe your analysis needs...",
      send: "Send",
      stop: "Stop",
      emptyTitle: "Start Your Omics Analysis",
      emptyDesc: "Enter your analysis request, or pick an example below to begin",
      typing: "Thinking...",
      modality: {
        auto: "Auto",
        scrna: "scRNA-seq",
        bulk: "Bulk RNA",
        spatial: "Spatial",
        tcr: "TCR",
        metagenomics: "Metagenomics",
        amplicon: "Amplicon",
      },
      examples: [
        "Run QC and clustering on this scRNA-seq data",
        "Find marker genes and run differential expression",
        "Check GPU availability",
        "Run bulk RNA-seq DE and enrichment analysis",
      ],
      plan: {
        title: "Analysis Plan",
      },
      tool: {
        running: "Running",
        success: "Completed",
        error: "Failed",
      },
    },
    data: {
      title: "Data Management",
      subtitle: "Manage multi-omics data files",
      upload: "Upload File",
      filterAll: "All",
      filterH5ad: ".h5ad",
      filterCsv: ".csv/.tsv",
      filterOther: "Other",
      empty: "No data files",
      emptyHint: "Upload .h5ad, .h5mu, .csv, .tsv, .fastq files",
      delete: "Delete",
      info: {
        title: "File Info",
        name: "Name",
        size: "Size",
        type: "Type",
        created: "Created",
        shape: "Shape",
      },
    },
    file: {
      upload: "Select or drag files here",
      uploading: "Uploading...",
      invalidType: "Unsupported file type",
      dropHere: "Drop files to upload",
    },
    settings: {
      title: "LLM Settings",
      subtitle: "Configure LLM API connection",
      addProvider: "Add Provider",
      noProviders: "No LLM providers configured",
      noProvidersHint: "Click a button above to add OpenAI, DeepSeek, or other compatible APIs",
      apiKey: "API Key",
      baseUrl: "Base URL",
      model: "Model",
      name: "Name",
      namePlaceholder: "Custom name",
      setActive: "Set Active",
      active: "Active",
      save: "Save Configuration",
      connected: "Connected",
      notConnected: "Not Connected",
      edit: "Edit",
      testConnection: "Test Connection",
      testing: "Testing...",
      testSuccess: "Connection successful!",
      testFailed: "Connection failed",
      saveSuccess: "Configuration saved",
      saveFailed: "Save failed",
    },
    status: {
      loading: "Loading...",
      error: "Error",
      retry: "Retry",
      success: "Success",
      noData: "No data",
    },
  },
};

export function createI18n() {
  const saved = localStorage.getItem("omics-copilot:lang");
  const locale = ref(saved && ["zh-CN", "en-US"].includes(saved) ? saved : "zh-CN");

  function t(key) {
    const keys = key.split(".");
    let val = messages[locale.value];
    for (const k of keys) {
      if (val == null) return key;
      val = val[k];
    }
    return val ?? key;
  }

  function setLocale(loc) {
    if (["zh-CN", "en-US"].includes(loc)) {
      locale.value = loc;
      localStorage.setItem("omics-copilot:lang", loc);
      document.documentElement.lang = loc;
    }
  }

  return { locale, t, setLocale };
}

export function useI18n() {
  const i18n = inject(I18N_KEY, null);
  if (!i18n) {
    const fallback = createI18n();
    provide(I18N_KEY, fallback);
    return fallback;
  }
  return i18n;
}
