package com.chargecloud.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.chargecloud.entity.Station;
import com.chargecloud.mapper.StationMapper;
import com.chargecloud.service.StationService;
import org.springframework.stereotype.Service;

@Service
public class StationServiceImpl extends ServiceImpl<StationMapper, Station> implements StationService {
}