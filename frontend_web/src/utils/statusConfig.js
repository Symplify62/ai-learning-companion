import {
  EllipsisHorizontalCircleIcon,
  Cog6ToothIcon,
  MagnifyingGlassIcon,
  PencilSquareIcon,
  LightBulbIcon,
  SparklesIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline';
import {
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon,
  CheckBadgeIcon
} from '@heroicons/react/24/solid';

const statusConfig = {
  processing_initiated: {
    displayText: '正在初始化处理...',
    IconComponent: EllipsisHorizontalCircleIcon,
    iconColorClass: 'text-blue-500',
  },
  a1_preprocessing_active: {
    displayText: '正在预处理内容...',
    IconComponent: Cog6ToothIcon,
    iconColorClass: 'text-blue-500',
    stageNumber: 1,
  },
  a1_processing_complete: {
    displayText: '内容预处理完成。',
    IconComponent: CheckCircleIcon,
    iconColorClass: 'text-green-500',
  },
  a2_extraction_active: {
    displayText: '正在提取关键信息...',
    IconComponent: MagnifyingGlassIcon,
    iconColorClass: 'text-blue-500',
    stageNumber: 2,
  },
  a2_extraction_complete: {
    displayText: '关键信息提取完成。',
    IconComponent: CheckCircleIcon,
    iconColorClass: 'text-green-500',
  },
  note_generation_active: {
    displayText: '正在生成学习笔记...',
    IconComponent: PencilSquareIcon,
    iconColorClass: 'text-blue-500',
    stageNumber: 3,
  },
  note_generation_complete: {
    displayText: '学习笔记生成完成。',
    IconComponent: CheckCircleIcon,
    iconColorClass: 'text-green-500',
  },
  knowledge_cues_generation_active: {
    displayText: '正在生成知识提示...',
    IconComponent: LightBulbIcon,
    iconColorClass: 'text-blue-500',
    stageNumber: 4,
  },
  knowledge_cues_generation_complete: {
    displayText: '知识提示生成完成。',
    IconComponent: CheckCircleIcon, // Using CheckCircleIcon as per table
    iconColorClass: 'text-green-500',
  },
  all_processing_complete: {
    displayText: '处理完成！学习资料已就绪。',
    IconComponent: SparklesIcon, // As per table (alternative CheckBadgeIcon also imported)
    iconColorClass: 'text-purple-600', // Using purple for a distinct final success
  },
  error_in_a1_llm: {
    displayText: '预处理出错，请重试。',
    IconComponent: ExclamationTriangleIcon,
    iconColorClass: 'text-red-500',
    isError: true,
  },
  error_in_a2_llm: {
    displayText: '信息提取出错，请重试。',
    IconComponent: ExclamationTriangleIcon,
    iconColorClass: 'text-red-500',
    isError: true,
  },
  error_in_b_llm: {
    displayText: '笔记生成出错，请重试。',
    IconComponent: ExclamationTriangleIcon,
    iconColorClass: 'text-red-500',
    isError: true,
  },
  error_in_d_llm: {
    displayText: '知识提示生成出错，请重试。',
    IconComponent: ExclamationTriangleIcon,
    iconColorClass: 'text-red-500',
    isError: true,
  },
  error_in_processing: {
    displayText: '处理中断，请稍后重试。',
    IconComponent: XCircleIcon,
    iconColorClass: 'text-red-600',
    isError: true,
  },
  default: {
    displayTextFunction: (status) => `当前状态: ${status || '未知'}`,
    IconComponent: InformationCircleIcon,
    iconColorClass: 'text-gray-500',
  },
};

/**
 * 获取给定状态字符串的显示属性。
 * @param {string} status - 后端返回的原始状态字符串。
 * @returns {{text: string, Icon: React.ComponentType, color: string, isError: boolean}}
 */
export function getStatusDisplay(status) {
  const config = statusConfig[status] || statusConfig.default;
  
  let text;
  if (config.displayTextFunction) {
    text = config.displayTextFunction(status);
  } else {
    text = config.displayText;
  }

  if (config.stageNumber) {
    text = `${text} (阶段 ${config.stageNumber}/4)`;
  }

  return {
    text,
    Icon: config.IconComponent,
    color: config.iconColorClass,
    isError: !!config.isError,
  };
} 