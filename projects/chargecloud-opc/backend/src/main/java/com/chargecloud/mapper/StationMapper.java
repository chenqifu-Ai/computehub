package com.chargecloud.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.chargecloud.entity.Station;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface StationMapper extends BaseMapper<Station> {
}