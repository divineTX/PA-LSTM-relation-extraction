#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# @Version : Python 3.6

import os
import torch
import torch.nn as nn
import torch.optim as optim

from config import Config
from utils import WordEmbeddingLoader, RelationLoader, TacredDataLoader
from model import PA_LSTM
from evaluate import Eval


def change_lr(optimizer, new_lr):
    for param_group in optimizer.param_groups:
        param_group['lr'] = new_lr


def train(model, criterion, loader, config):
    train_loader, dev_loader, _ = loader
    optimizer = optim.SGD(model.parameters(), lr=config.lr)

    print(model)
    print('traning model parameters:')
    for name, param in model.named_parameters():
        if param.requires_grad:
            print('%s :  %s' % (name, str(param.data.shape)))
    print('--------------------------------------')
    print('start to train the model ...')

    eval_tool = Eval(config)
    min_f1 = -float('inf')
    current_lr = config.lr
    global_step = 0
    for epoch in range(1, config.epoch+1):
        if epoch > 10:
            current_lr *= 0.9
            change_lr(optimizer, current_lr)

        for step, (data, label) in enumerate(train_loader):
            model.train()
            data = data.to(config.device)
            label = label.to(config.device)

            optimizer.zero_grad()
            logits = model(data)
            loss = criterion(logits, label)
            loss.backward()
            optimizer.step()

            global_step += 1
            if global_step % 200 == 0:
                _, train_loss, _ = eval_tool.evaluate(model, criterion, train_loader)
                f1, dev_loss, _ = eval_tool.evaluate(model, criterion, dev_loader)

                print('[%03d] train_loss: %.3f | dev_loss: %.3f | micro f1 on dev: %.4f'
                      % (epoch, train_loss, dev_loss, f1), end=' ')
                if f1 > min_f1:
                    min_f1 = f1
                    torch.save(model.state_dict(), os.path.join(config.model_dir, 'model.pkl'))
                    print('>>> save models!')
                else:
                    print()


def test(model, criterion, loader, config):
    print('--------------------------------------')
    print('start test ...')

    _, _, test_loader = loader
    model.load_state_dict(torch.load(os.path.join(config.model_dir, 'model.pkl')))
    eval_tool = Eval(config)
    f1, test_loss, preds = eval_tool.evaluate(model, criterion, test_loader)
    print('test_loss: %.3f | micro f1 on test:  %.4f' % (test_loss, f1))


if __name__ == '__main__':
    config = Config()
    print('--------------------------------------')
    print('some config:')
    config.print_config()

    print('--------------------------------------')
    print('start to load data ...')
    word2id, word_vec = WordEmbeddingLoader(config).load_embedding()
    rel2id, _, class_num = RelationLoader(config).get_relation()
    loader = TacredDataLoader(rel2id, word2id, config)

    train_loader, dev_loader = None, None
    if config.mode == 1:  # train mode
        train_loader = loader.get_train()
        dev_loader = loader.get_dev()
    test_loader = loader.get_test()
    loader = [train_loader, dev_loader, test_loader]
    print('finish!')

    print('--------------------------------------')
    model = PA_LSTM(word_vec=word_vec, class_num=class_num, config=config)
    model = model.to(config.device)
    criterion = nn.CrossEntropyLoss()

    if config.mode == 1:  # train mode
        train(model, criterion, loader, config)
    test(model, criterion, loader, config)
