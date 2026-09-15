import {
  BadRequestException,
  Controller,
  Post,
  UploadedFile,
  UseInterceptors,
} from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { memoryStorage } from 'multer';
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
}
