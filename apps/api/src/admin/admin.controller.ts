import {
  Controller,
  Get,
  Param,
  Res,
  UseGuards,
} from '@nestjs/common';
import type { Response } from 'express';
import { AdminGuard } from './admin.guard';
import { AdminService } from './admin.service';

@Controller('admin')
@UseGuards(AdminGuard)
export class AdminController {
  constructor(private readonly admin: AdminService) {}

  @Get('overview')
  overview() {
    return this.admin.overview();
  }

  @Get('feedback')
  feedback() {
    return this.admin.feedbackList();
  }

  @Get('feedback/:id/image')
  async feedbackImage(@Param('id') id: string, @Res() response: Response) {
    const image = await this.admin.feedbackImage(id);
    return response.type(image.mimeType).sendFile(image.path);
  }
}
