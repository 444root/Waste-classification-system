import {
  BadRequestException,
  Body,
  Controller,
  Post,
  Req,
  UploadedFile,
  UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import type { Request } from 'express';
import { memoryStorage } from 'multer';
import type { PublicUser } from '../auth/auth.service';
import { ClassificationFeedbackDto } from './dto/classification-feedback.dto';
import { ClassificationsService } from './classifications.service';

const ALLOWED_TYPES = new Set([
  'image/jpeg',
  'image/png',
  'image/webp',
  'image/heic',
  'image/heif',
]);

@Controller('classifications')
export class ClassificationsController {
  constructor(private readonly classifications: ClassificationsService) {}

  @Post()
  @UseInterceptors(
    FileInterceptor('file', {
      storage: memoryStorage(),
      limits: { fileSize: 12 * 1024 * 1024, files: 1 },
    }),
  )
  classify(@UploadedFile() file?: Express.Multer.File) {
    if (!file) throw new BadRequestException('Choose an image to classify');
    const isHeifFile = /\.(heic|heif)$/i.test(file.originalname);
    if (!ALLOWED_TYPES.has(file.mimetype) && !isHeifFile) {
      throw new BadRequestException(
        'Only JPG, PNG, WebP, HEIC and HEIF images are allowed',
      );
    }
    return this.classifications.classify(file);
  }

  @Post('feedback')
  @UseInterceptors(
    FileInterceptor('file', {
      storage: memoryStorage(),
      limits: { fileSize: 12 * 1024 * 1024, files: 1 },
    }),
  )
  feedback(
    @Req() request: Request & { user: PublicUser },
    @Body() dto: ClassificationFeedbackDto,
    @UploadedFile() file?: Express.Multer.File,
  ) {
    if (!file) throw new BadRequestException('Include the classified image');
    const isHeifFile = /\.(heic|heif)$/i.test(file.originalname);
    if (!ALLOWED_TYPES.has(file.mimetype) && !isHeifFile) {
      throw new BadRequestException(
        'Only JPG, PNG, WebP, HEIC and HEIF images are allowed',
      );
    }
    return this.classifications.saveFeedback(file, request.user.id, dto);
  }
}
