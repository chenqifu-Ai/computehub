/**
 * 主题系统
 * 提供多种主题配置支持
 */

/**
 * 默认亮色主题
 */
export const defaultTheme = {
  name: 'light',
  colors: {
    primary: '#007bff',
    secondary: '#6c757d',
    success: '#28a745',
    danger: '#dc3545',
    warning: '#ffc107',
    info: '#17a2b8',
    
    background: '#ffffff',
    surface: '#f8f9fa',
    text: '#333333',
    textSecondary: '#6c757d',
    border: '#e0e0e0',
    
    // 图表颜色
    chart: {
      blue: '#007bff',
      green: '#28a745',
      red: '#dc3545',
      orange: '#fd7e14',
      purple: '#6f42c1',
      teal: '#20c997'
    }
  },
  typography: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    fontSize: {
      xs: '0.75rem',
      sm: '0.875rem',
      base: '1rem',
      lg: '1.125rem',
      xl: '1.25rem',
      '2xl': '1.5rem'
    },
    fontWeight: {
      light: 300,
      normal: 400,
      medium: 500,
      semibold: 600,
      bold: 700
    }
  },
  spacing: {
    xs: '0.25rem',
    sm: '0.5rem',
    md: '1rem',
    lg: '1.5rem',
    xl: '2rem',
    '2xl': '3rem'
  },
  borderRadius: {
    sm: '0.25rem',
    md: '0.375rem',
    lg: '0.5rem',
    xl: '0.75rem'
  },
  shadows: {
    sm: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
    md: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
    lg: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
    xl: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
  }
};

/**
 * 暗色主题
 */
export const darkTheme = {
  ...defaultTheme,
  name: 'dark',
  colors: {
    ...defaultTheme.colors,
    background: '#1a1a1a',
    surface: '#2d3748',
    text: '#ffffff',
    textSecondary: '#a0aec0',
    border: '#4a5568'
  }
};

/**
 * 专业蓝色主题
 */
export const blueTheme = {
  ...defaultTheme,
  name: 'blue',
  colors: {
    ...defaultTheme.colors,
    primary: '#1e40af',
    secondary: '#475569',
    background: '#f1f5f9',
    surface: '#e2e8f0'
  }
};

/**
 * 绿色环保主题
 */
export const greenTheme = {
  ...defaultTheme,
  name: 'green',
  colors: {
    ...defaultTheme.colors,
    primary: '#059669',
    secondary: '#475569',
    background: '#f0fdf4',
    surface: '#dcfce7'
  }
};

/**
 * 获取主题配置
 * @param {string} themeName 主题名称
 * @returns {Object} 主题配置对象
 */
export function getTheme(themeName = 'light') {
  const themes = {
    light: defaultTheme,
    dark: darkTheme,
    blue: blueTheme,
    green: greenTheme
  };
  
  return themes[themeName] || defaultTheme;
}

/**
 * 应用主题到CSS变量
 * @param {Object} theme 主题配置
 * @param {string} selector 选择器
 */
export function applyTheme(theme, selector = ':root') {
  if (typeof document === 'undefined') return;
  
  const style = document.createElement('style');
  style.id = 'decision-viz-theme';
  
  let css = `${selector} {\n`;
  
  // 应用颜色变量
  Object.entries(theme.colors).forEach(([key, value]) => {
    if (typeof value === 'object') {
      Object.entries(value).forEach(([subKey, subValue]) => {
        css += `  --dv-color-${key}-${subKey}: ${subValue};\n`;
      });
    } else {
      css += `  --dv-color-${key}: ${value};\n`;
    }
  });
  
  // 应用排版变量
  Object.entries(theme.typography).forEach(([key, value]) => {
    if (typeof value === 'object') {
      Object.entries(value).forEach(([subKey, subValue]) => {
        css += `  --dv-${key}-${subKey}: ${subValue};\n`;
      });
    } else {
      css += `  --dv-${key}: ${value};\n`;
    }
  });
  
  css += '}';
  
  // 移除旧主题
  const oldStyle = document.getElementById('decision-viz-theme');
  if (oldStyle) {
    document.head.removeChild(oldStyle);
  }
  
  style.textContent = css;
  document.head.appendChild(style);
}

/**
 * 创建自定义主题
 * @param {Object} baseTheme 基础主题
 * @param {Object} overrides 覆盖配置
 * @returns {Object} 自定义主题
 */
export function createCustomTheme(baseTheme = defaultTheme, overrides = {}) {
  return {
    ...baseTheme,
    ...overrides,
    colors: {
      ...baseTheme.colors,
      ...overrides.colors
    },
    typography: {
      ...baseTheme.typography,
      ...overrides.typography
    }
  };
}