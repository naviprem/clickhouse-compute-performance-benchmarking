import React from 'react';
import ReactECharts from 'echarts-for-react';

const MetricsChart = ({ data, metricName, source }) => {
  const option = {
    title: {
      text: `${metricName} - ${source === 'option1' ? 'Option 1 (S3)' : 'Option 2 (Ingested)'}`,
      left: 'center',
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
      },
    },
    legend: {
      data: ['Average', 'Min', 'Max'],
      top: 30,
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data.map(d => d.time),
    },
    yAxis: {
      type: 'value',
      name: 'Value',
    },
    series: [
      {
        name: 'Average',
        type: 'line',
        data: data.map(d => d.avg_value),
        smooth: true,
        lineStyle: {
          width: 2,
        },
      },
      {
        name: 'Min',
        type: 'line',
        data: data.map(d => d.min_value),
        smooth: true,
        lineStyle: {
          type: 'dashed',
        },
      },
      {
        name: 'Max',
        type: 'line',
        data: data.map(d => d.max_value),
        smooth: true,
        lineStyle: {
          type: 'dashed',
        },
      },
    ],
  };

  return (
    <ReactECharts
      option={option}
      style={{ height: '400px', width: '100%' }}
      notMerge={true}
      lazyUpdate={true}
    />
  );
};

export default MetricsChart;