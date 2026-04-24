package com.chargecloud.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.chargecloud.entity.Pile;
import com.chargecloud.mapper.PileMapper;
import com.chargecloud.service.PileService;
import org.springframework.stereotype.Service;

@Service
public class PileServiceImpl extends ServiceImpl<PileMapper, Pile> implements PileService {
}